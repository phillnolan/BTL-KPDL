from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from .arff import convert_csv_to_arff
from .config import get_nested, load_config, resolve_path
from .datasets import scan_dataset
from .features import extract_cube_features
from .grid import generate_grid, grid_to_json
from .readers import iter_preprocessed_frames, probe_video
from .records import FrameRecord, VideoSource
from .schema import FRAME_MANIFEST_COLUMNS, SCHEMA_VERSION, VIDEO_MANIFEST_COLUMNS, feature_columns
from .utils import ensure_dir


def run_preprocess(
    config_path: str | Path,
    project_root: str | Path,
    output_root: str | Path | None = None,
    split: str | None = None,
    limit_videos: int | None = None,
    limit_frames: int | None = None,
    progress_every: int | None = None,
    export_arff: bool = False,
) -> dict:
    config = load_config(config_path)
    project_root = Path(project_root).resolve()
    dataset = str(get_nested(config, "data", "dataset"))
    direction_bins = int(get_nested(config, "features", "direction_bins", default=8))
    resize_width = int(get_nested(config, "video", "resize_width"))
    resize_height = int(get_nested(config, "video", "resize_height"))
    grid_rows = int(get_nested(config, "grid", "rows"))
    grid_cols = int(get_nested(config, "grid", "cols"))
    ignore_cells = list(get_nested(config, "grid", "ignore_cells", default=[]) or [])
    cube_length = int(get_nested(config, "cube", "length"))
    cube_stride = int(get_nested(config, "cube", "stride"))

    output_root_value = output_root or get_nested(config, "output", "root", default="outputs/preprocessed")
    output_base = ensure_dir(resolve_path(output_root_value, project_root) / dataset)

    cells = generate_grid(resize_width, resize_height, grid_rows, grid_cols, ignore_cells)
    grid_payload = grid_to_json(cells, resize_width, resize_height, grid_rows, grid_cols)
    with (output_base / "grid.json").open("w", encoding="utf-8") as handle:
        json.dump(grid_payload, handle, indent=2)

    sources = scan_dataset(config, project_root, split)
    sources = _limit_sources_per_split(sources, limit_videos)
    active_splits = sorted({source.split for source in sources} or ({split} if split else {"train", "test"}))

    stats = _new_stats(dataset, grid_payload, config_path, active_splits, direction_bins)
    feature_paths: dict[str, Path] = {}

    with (output_base / "frames_manifest.csv").open("w", newline="", encoding="utf-8") as frames_file, (
        output_base / "videos_manifest.csv"
    ).open("w", newline="", encoding="utf-8") as videos_file:
        frame_writer = csv.DictWriter(frames_file, fieldnames=FRAME_MANIFEST_COLUMNS)
        video_writer = csv.DictWriter(videos_file, fieldnames=VIDEO_MANIFEST_COLUMNS)
        frame_writer.writeheader()
        video_writer.writeheader()

        feature_files = {}
        feature_writers = {}
        try:
            columns = feature_columns(direction_bins)
            for split_name in active_splits:
                feature_path = output_base / f"features_{split_name}.csv"
                feature_paths[split_name] = feature_path
                handle = feature_path.open("w", newline="", encoding="utf-8")
                feature_files[split_name] = handle
                writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                feature_writers[split_name] = writer

            source_total = len(sources)
            for source_index, source in enumerate(sources, start=1):
                _process_source(
                    source=source,
                    config=config,
                    cells=cells,
                    frame_writer=frame_writer,
                    video_writer=video_writer,
                    feature_writer=feature_writers[source.split],
                    stats=stats,
                    source_index=source_index,
                    source_total=source_total,
                    cube_length=cube_length,
                    cube_stride=cube_stride,
                    limit_frames=limit_frames,
                    progress_every=progress_every,
                )
        finally:
            for handle in feature_files.values():
                handle.close()

    _finalize_stats(stats)

    stats["output_dir"] = str(output_base)

    stats_path = output_base / "preprocess_stats.json"
    with stats_path.open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)

    arff_paths: list[str] = []
    if export_arff:
        weka_root_value = get_nested(config, "output", "weka_root", default="src/outputs/weka")
        weka_root = ensure_dir(resolve_path(weka_root_value, project_root))
        for split_name, feature_path in feature_paths.items():
            arff_path = weka_root / f"{dataset}_features_{split_name}.arff"
            convert_csv_to_arff(feature_path, arff_path, relation=f"{dataset}_features_{split_name}")
            arff_paths.append(str(arff_path))
        stats["arff_outputs"] = arff_paths
        with stats_path.open("w", encoding="utf-8") as handle:
            json.dump(stats, handle, indent=2)

    return stats


def _process_source(
    source: VideoSource,
    config: dict,
    cells: list,
    frame_writer: csv.DictWriter,
    video_writer: csv.DictWriter,
    feature_writer: csv.DictWriter,
    stats: dict,
    source_index: int,
    source_total: int,
    cube_length: int,
    cube_stride: int,
    limit_frames: int | None,
    progress_every: int | None,
) -> None:
    split_stats = stats["splits"][source.split]
    split_stats["num_videos"] += 1

    video_probe = probe_video(source)
    num_frames = 0
    num_cubes = 0
    original_width = video_probe.get("original_width")
    original_height = video_probe.get("original_height")
    expected_frames = _expected_frame_count(video_probe.get("num_frames_hint"), limit_frames)
    buffer: deque[FrameRecord] = deque(maxlen=cube_length)
    should_log_progress = progress_every is not None and progress_every > 0

    if should_log_progress:
        _progress(
            f"[{source_index}/{source_total}] {source.split}/{source.video_id}: "
            f"start, expected_frames={_blank_none(expected_frames)}"
        )

    try:
        for frame in iter_preprocessed_frames(source, config, limit_frames=limit_frames):
            num_frames += 1
            if original_width is None:
                original_width = frame.original_width
            if original_height is None:
                original_height = frame.original_height
            frame_writer.writerow(_frame_manifest_row(frame))
            buffer.append(frame)

            if len(buffer) == cube_length:
                start_index = num_frames - cube_length
                if start_index % cube_stride == 0:
                    num_cubes += 1
                    cube = list(buffer)
                    cube_id = f"{source.video_id}_{cube[0].frame_id:06d}_{cube[-1].frame_id:06d}"
                    rows = extract_cube_features(cube_id, cube, cells, config)
                    for row in rows:
                        feature_writer.writerow(row)
                        split_stats["num_feature_rows"] += 1
                        split_stats["_motion_density_sum"] += float(row["motion_density"])
                        split_stats["_brightness_sum"] += float(row["brightness_mean"])
                        split_stats["_feature_value_count"] += 1
            if should_log_progress and num_frames % progress_every == 0:
                _progress(
                    f"[{source_index}/{source_total}] {source.split}/{source.video_id}: "
                    f"frames={num_frames}{_progress_total(expected_frames)}, cubes={num_cubes}"
                )

        split_stats["num_frames"] += num_frames
        split_stats["num_cubes"] += num_cubes
        if expected_frames is not None and num_frames < expected_frames:
            split_stats["missing_frames"] += expected_frames - num_frames
        video_writer.writerow(
            {
                "dataset": source.dataset,
                "split": source.split,
                "video_id": source.video_id,
                "source_path": str(source.source_path),
                "input_type": source.input_type,
                "fps": _blank_none(video_probe.get("fps")),
                "num_frames": num_frames,
                "num_cubes": num_cubes,
                "original_width": _blank_none(original_width),
                "original_height": _blank_none(original_height),
                "failed": False,
                "error": "",
            }
        )
        if should_log_progress:
            _progress(
                f"[{source_index}/{source_total}] {source.split}/{source.video_id}: "
                f"done, frames={num_frames}{_progress_total(expected_frames)}, cubes={num_cubes}"
            )
    except Exception as exc:
        split_stats["failed_videos"] += 1
        video_writer.writerow(
            {
                "dataset": source.dataset,
                "split": source.split,
                "video_id": source.video_id,
                "source_path": str(source.source_path),
                "input_type": source.input_type,
                "fps": _blank_none(video_probe.get("fps")),
                "num_frames": num_frames,
                "num_cubes": num_cubes,
                "original_width": _blank_none(original_width),
                "original_height": _blank_none(original_height),
                "failed": True,
                "error": str(exc),
            }
        )
        if should_log_progress:
            _progress(
                f"[{source_index}/{source_total}] {source.split}/{source.video_id}: "
                f"failed after frames={num_frames}, error={exc}"
            )


def _frame_manifest_row(frame: FrameRecord) -> dict[str, object]:
    return {
        "dataset": frame.dataset,
        "split": frame.split,
        "video_id": frame.video_id,
        "frame_id": frame.frame_id,
        "timestamp": _blank_none(frame.timestamp),
        "source_path": str(frame.source_path),
        "original_width": frame.original_width,
        "original_height": frame.original_height,
        "resized_width": frame.resized_width,
        "resized_height": frame.resized_height,
    }


def _limit_sources_per_split(sources: list[VideoSource], limit_videos: int | None) -> list[VideoSource]:
    if limit_videos is None:
        return sources
    counts: dict[str, int] = defaultdict(int)
    limited: list[VideoSource] = []
    for source in sources:
        if counts[source.split] >= limit_videos:
            continue
        limited.append(source)
        counts[source.split] += 1
    return limited


def _new_stats(
    dataset: str,
    grid_payload: dict,
    config_path: str | Path,
    splits: list[str],
    direction_bins: int,
) -> dict:
    return {
        "dataset": dataset,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "schema": {
            "version": SCHEMA_VERSION,
            "frames_manifest_columns": FRAME_MANIFEST_COLUMNS,
            "videos_manifest_columns": VIDEO_MANIFEST_COLUMNS,
            "feature_columns": feature_columns(direction_bins),
        },
        "grid": {
            "rows": grid_payload["rows"],
            "cols": grid_payload["cols"],
            "num_cells": grid_payload["num_cells"],
            "resized_width": grid_payload["resized_width"],
            "resized_height": grid_payload["resized_height"],
        },
        "splits": {split: _empty_split_stats(grid_payload["num_cells"]) for split in splits},
    }


def _empty_split_stats(num_cells: int) -> dict:
    return {
        "num_videos": 0,
        "num_frames": 0,
        "num_cubes": 0,
        "num_cells": num_cells,
        "num_feature_rows": 0,
        "missing_frames": 0,
        "failed_videos": 0,
        "avg_motion_density": 0.0,
        "avg_brightness": 0.0,
        "_motion_density_sum": 0.0,
        "_brightness_sum": 0.0,
        "_feature_value_count": 0,
    }


def _finalize_stats(stats: dict) -> None:
    for split_stats in stats["splits"].values():
        count = split_stats.pop("_feature_value_count", 0)
        motion_sum = split_stats.pop("_motion_density_sum", 0.0)
        brightness_sum = split_stats.pop("_brightness_sum", 0.0)
        if count:
            split_stats["avg_motion_density"] = motion_sum / count
            split_stats["avg_brightness"] = brightness_sum / count


def _blank_none(value: object) -> object:
    return "" if value is None else value


def _expected_frame_count(num_frames_hint: object, limit_frames: int | None) -> int | None:
    try:
        hint = int(num_frames_hint) if num_frames_hint is not None else None
    except (TypeError, ValueError):
        hint = None
    if hint is not None and hint <= 0:
        hint = None
    if limit_frames is not None:
        return min(limit_frames, hint) if hint is not None else limit_frames
    return hint


def _progress_total(expected_frames: int | None) -> str:
    return f"/{expected_frames}" if expected_frames is not None else ""


def _progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)
