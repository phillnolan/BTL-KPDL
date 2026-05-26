from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from kpdl_preprocess.config import ConfigError, resolve_path
from kpdl_preprocess.utils import ensure_dir

from .config import AnomalyConfig, load_anomaly_config
from .frames import ensure_preprocessed_frame_source, load_preprocessed_frames
from .io import read_json, require_files, write_json
from .qualitative import write_qualitative_report


@dataclass(frozen=True)
class GridCell:
    cell_id: str
    row: int
    col: int
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass(frozen=True)
class GridSpec:
    resized_width: int
    resized_height: int
    rows: int
    cols: int
    cells: dict[str, GridCell]


@dataclass(frozen=True)
class FrameScore:
    dataset: str
    video_id: str
    frame_id: int
    frame_score: float
    smoothed_frame_score: float
    severity: str
    top_cells: list[str]


@dataclass
class FrameSelection:
    dataset: str
    video_id: str
    frame_id: int
    frame_score: float
    smoothed_frame_score: float
    severity: str
    top_cells: list[str]
    selection_type: str
    rank: int = 0
    alert_id: str | None = None
    alert_start_frame_id: int | None = None
    alert_end_frame_id: int | None = None
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VisualizationSettings:
    output_dir: Path
    colormap: str
    alpha: float
    heatmap_normalization: str
    draw_grid: bool
    draw_top_cells: bool
    top_cells_per_frame: int
    top_frames: int
    min_score: float
    frame_source: str
    image_format: str
    video_fps: float


def run_visualization(
    config_path: str | Path,
    project_root: str | Path = ".",
    result_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    top_frames: int | None = None,
    include_alerts: bool = False,
    video_id: str | None = None,
    start_frame: int | None = None,
    end_frame: int | None = None,
    write_video: bool = False,
    alpha: float | None = None,
    colormap: str | None = None,
    min_score: float | None = None,
    limit_frames: int | None = None,
) -> dict[str, Any]:
    config = load_anomaly_config(config_path=config_path, project_root=project_root)
    settings = _settings(config, output_dir, alpha, colormap, min_score)
    ensure_preprocessed_frame_source(settings.frame_source)
    output_path = ensure_dir(settings.output_dir)

    result_path = resolve_path(result_dir, config.project_root) if result_dir is not None else config.result_dir
    frame_scores_path = result_path / "frame_scores.csv"
    cell_scores_path = result_path / "cell_scores.csv"
    alerts_path = result_path / "alerts.json"
    require_files([config.grid_path, frame_scores_path, cell_scores_path])

    grid = load_grid(config.grid_path)
    frame_scores = load_frame_scores(frame_scores_path)
    alerts = load_alerts(alerts_path) if alerts_path.exists() else []

    top_count = _top_count(settings, top_frames, include_alerts, video_id)
    selections: list[FrameSelection] = []
    selected_alerts: list[dict[str, Any]] = []

    if top_count > 0:
        selections.extend(
            select_top_frames(
                frame_scores=frame_scores,
                count=top_count,
                min_score=settings.min_score,
                video_id=video_id if start_frame is None and end_frame is None else None,
            )
        )

    if include_alerts:
        alert_selections, selected_alerts = select_alert_peaks(
            frame_scores=frame_scores,
            alerts=alerts,
            limit=limit_frames,
        )
        selections.extend(alert_selections)

    if video_id is not None and not write_video and top_frames is None and not include_alerts:
        selections.extend(
            select_video_range(
                frame_scores=frame_scores,
                video_id=video_id,
                start_frame=start_frame,
                end_frame=end_frame,
                limit=limit_frames,
            )
        )

    image_keys = {(selection.video_id, selection.frame_id) for selection in selections}
    video_selections: list[FrameSelection] = []
    if write_video:
        video_selections = select_video_range(
            frame_scores=frame_scores,
            video_id=video_id or _default_video_id(frame_scores, alerts),
            start_frame=start_frame,
            end_frame=end_frame,
            limit=limit_frames,
            selection_type="video_frame",
        )
    video_keys = {(selection.video_id, selection.frame_id) for selection in video_selections}
    requested_keys = image_keys | video_keys

    cell_scores, global_max, missing_cell_score_frames = load_selected_cell_scores(
        cell_scores_path,
        requested_keys,
    )
    frame_batch = load_preprocessed_frames(config, _requests_by_video(requested_keys))

    index_records: list[dict[str, Any]] = []
    images_written = 0
    for selection in selections:
        loaded_frame = frame_batch.frames.get((selection.video_id, selection.frame_id))
        if loaded_frame is None:
            continue
        score_rows = cell_scores.get((selection.video_id, selection.frame_id), [])
        category = "alerts" if selection.selection_type == "alert_peak" else "top_frames"
        image_path = _image_path(output_path, category, selection, settings.image_format)
        overlay = render_overlay(
            frame_gray=loaded_frame.gray,
            score_rows=score_rows,
            grid=grid,
            top_cells=selection.top_cells[: settings.top_cells_per_frame],
            settings=settings,
            global_max=global_max,
        )
        _write_image(image_path, overlay)
        images_written += 1
        index_records.append(_index_record(config, output_path, image_path, selection))

    video_records: list[dict[str, Any]] = []
    if write_video and video_selections:
        video_record = _write_video_overlay(
            config=config,
            output_dir=output_path,
            frame_batch=frame_batch,
            cell_scores=cell_scores,
            grid=grid,
            selections=video_selections,
            settings=settings,
            global_max=global_max,
        )
        if video_record is not None:
            video_records.append(video_record)

    stats = {
        "dataset": config.dataset,
        "config_path": str(config.config_path),
        "result_dir": _display_path(result_path, config.project_root),
        "grid_path": _display_path(config.grid_path, config.project_root),
        "output_dir": _display_path(output_path, config.project_root),
        "num_frames_selected": len(selections),
        "num_images_written": images_written,
        "num_videos_written": len(video_records),
        "missing_frames": frame_batch.missing,
        "missing_cell_score_frames": missing_cell_score_frames,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frame_source": settings.frame_source,
        "heatmap_normalization": settings.heatmap_normalization,
        "alpha": settings.alpha,
        "colormap": settings.colormap,
        "video_records": video_records,
    }

    write_json(output_path / "visualization_index.json", _public_index(index_records))
    write_json(output_path / "visualization_stats.json", stats)
    write_qualitative_report(
        output_path / "qualitative_report.md",
        dataset=config.dataset,
        index_records=index_records,
        alert_records=selected_alerts,
        video_records=video_records,
        stats=stats,
    )
    return stats


def load_grid(path: str | Path) -> GridSpec:
    payload = read_json(path)
    width = int(payload["resized_width"])
    height = int(payload["resized_height"])
    cells: dict[str, GridCell] = {}
    for item in payload.get("cells", []):
        cell = GridCell(
            cell_id=str(item["cell_id"]),
            row=int(item["row"]),
            col=int(item["col"]),
            x1=int(item["x1"]),
            y1=int(item["y1"]),
            x2=int(item["x2"]),
            y2=int(item["y2"]),
        )
        if cell.x1 < 0 or cell.y1 < 0 or cell.x2 > width or cell.y2 > height:
            raise ConfigError(f"Grid cell {cell.cell_id} is outside resized frame bounds")
        if cell.x2 <= cell.x1 or cell.y2 <= cell.y1:
            raise ConfigError(f"Grid cell {cell.cell_id} has invalid bounds")
        cells[cell.cell_id] = cell
    expected = int(payload["rows"]) * int(payload["cols"])
    if len(cells) > expected:
        raise ConfigError(f"Grid has {len(cells)} cells, more than rows*cols={expected}")
    return GridSpec(
        resized_width=width,
        resized_height=height,
        rows=int(payload["rows"]),
        cols=int(payload["cols"]),
        cells=cells,
    )


def load_frame_scores(path: str | Path) -> list[FrameScore]:
    scores: list[FrameScore] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            scores.append(
                FrameScore(
                    dataset=str(row["dataset"]),
                    video_id=str(row["video_id"]),
                    frame_id=int(row["frame_id"]),
                    frame_score=float(row["frame_score"]),
                    smoothed_frame_score=float(row["smoothed_frame_score"]),
                    severity=str(row["severity"]),
                    top_cells=_parse_top_cells(row.get("top_cells", "")),
                )
            )
    return scores


def load_alerts(path: str | Path) -> list[dict[str, Any]]:
    alerts = read_json(path)
    normalized: list[dict[str, Any]] = []
    for alert in alerts:
        item = dict(alert)
        item["start_frame_id"] = int(item["start_frame_id"])
        item["end_frame_id"] = int(item["end_frame_id"])
        item["max_score"] = float(item.get("max_score", 0.0))
        item["alert_id"] = f"{item.get('video_id')}:{item['start_frame_id']}-{item['end_frame_id']}"
        normalized.append(item)
    return normalized


def select_top_frames(
    frame_scores: list[FrameScore],
    count: int,
    min_score: float,
    video_id: str | None = None,
) -> list[FrameSelection]:
    candidates = [
        score
        for score in frame_scores
        if score.smoothed_frame_score >= min_score and (video_id is None or score.video_id == video_id)
    ]
    candidates.sort(key=lambda item: item.smoothed_frame_score, reverse=True)
    return [
        _selection_from_score(score, "top_frame", rank=index)
        for index, score in enumerate(candidates[:count], start=1)
    ]


def select_alert_peaks(
    frame_scores: list[FrameScore],
    alerts: list[dict[str, Any]],
    limit: int | None = None,
) -> tuple[list[FrameSelection], list[dict[str, Any]]]:
    by_video: dict[str, list[FrameScore]] = {}
    for score in frame_scores:
        by_video.setdefault(score.video_id, []).append(score)
    for scores in by_video.values():
        scores.sort(key=lambda item: item.frame_id)

    selections: list[FrameSelection] = []
    selected_alerts: list[dict[str, Any]] = []
    for index, alert in enumerate(alerts, start=1):
        if limit is not None and len(selections) >= limit:
            break
        video_scores = by_video.get(str(alert.get("video_id")), [])
        in_range = [
            score
            for score in video_scores
            if int(alert["start_frame_id"]) <= score.frame_id <= int(alert["end_frame_id"])
        ]
        if not in_range:
            continue
        peak = max(in_range, key=lambda item: item.smoothed_frame_score)
        selection = _selection_from_score(peak, "alert_peak", rank=index)
        selection.alert_id = str(alert["alert_id"])
        selection.alert_start_frame_id = int(alert["start_frame_id"])
        selection.alert_end_frame_id = int(alert["end_frame_id"])
        selection.reasons = list(alert.get("reasons", []))
        selections.append(selection)
        selected_alerts.append(alert)
    return selections, selected_alerts


def select_video_range(
    frame_scores: list[FrameScore],
    video_id: str,
    start_frame: int | None = None,
    end_frame: int | None = None,
    limit: int | None = None,
    selection_type: str = "range_frame",
) -> list[FrameSelection]:
    selected = [
        score
        for score in frame_scores
        if score.video_id == video_id
        and (start_frame is None or score.frame_id >= start_frame)
        and (end_frame is None or score.frame_id <= end_frame)
    ]
    selected.sort(key=lambda item: item.frame_id)
    if limit is not None:
        selected = selected[:limit]
    return [
        _selection_from_score(score, selection_type, rank=index)
        for index, score in enumerate(selected, start=1)
    ]


def load_selected_cell_scores(
    path: str | Path,
    selected_keys: set[tuple[str, int]],
) -> tuple[dict[tuple[str, int], list[dict[str, Any]]], float, list[dict[str, object]]]:
    scores: dict[tuple[str, int], list[dict[str, Any]]] = {key: [] for key in selected_keys}
    global_max = 0.0
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cell_score = float(row["cell_score"])
            global_max = max(global_max, cell_score)
            key = (str(row["video_id"]), int(row["center_frame_id"]))
            if key not in scores:
                continue
            scores[key].append(
                {
                    "cell_id": str(row["cell_id"]),
                    "cell_score": cell_score,
                    "cluster_distance_score": float(row["cluster_distance_score"]),
                    "temporal_change_score": float(row["temporal_change_score"]),
                    "cluster_distance": float(row["cluster_distance"]),
                    "cluster_threshold": float(row["cluster_threshold"]),
                    "nearest_cluster": int(row["nearest_cluster"]),
                }
            )
    missing = [
        {"video_id": video_id, "frame_id": frame_id}
        for video_id, frame_id in sorted(selected_keys)
        if not scores.get((video_id, frame_id))
    ]
    return scores, global_max, missing


def render_overlay(
    frame_gray: np.ndarray,
    score_rows: list[dict[str, Any]],
    grid: GridSpec,
    top_cells: list[str],
    settings: VisualizationSettings,
    global_max: float,
) -> np.ndarray:
    cv2 = _cv2()
    heatmap = np.zeros((grid.resized_height, grid.resized_width), dtype=np.float32)
    for row in score_rows:
        cell = grid.cells.get(str(row["cell_id"]))
        if cell is None:
            continue
        score = float(np.clip(float(row["cell_score"]), 0.0, 1.0))
        heatmap[cell.y1 : cell.y2, cell.x1 : cell.x2] = score

    if frame_gray.shape[:2] != heatmap.shape[:2]:
        heatmap = cv2.resize(heatmap, (frame_gray.shape[1], frame_gray.shape[0]), interpolation=cv2.INTER_NEAREST)

    normalized = _normalize_heatmap(heatmap, settings.heatmap_normalization, global_max)
    colored = cv2.applyColorMap((normalized * 255.0).astype(np.uint8), _colormap_id(settings.colormap))
    base = cv2.cvtColor(frame_gray, cv2.COLOR_GRAY2BGR) if frame_gray.ndim == 2 else frame_gray.copy()
    overlay = cv2.addWeighted(base, 1.0 - settings.alpha, colored, settings.alpha, 0.0)

    if settings.draw_grid:
        _draw_grid(overlay, grid)
    if settings.draw_top_cells:
        score_by_cell = {str(row["cell_id"]): float(row["cell_score"]) for row in score_rows}
        _draw_top_cells(overlay, grid, top_cells, score_by_cell)
    return overlay


def _settings(
    config: AnomalyConfig,
    output_dir: str | Path | None,
    alpha: float | None,
    colormap: str | None,
    min_score: float | None,
) -> VisualizationSettings:
    raw = config.raw.setdefault("visualization", {})
    output_root = raw.setdefault("output_root", "src/outputs/visualizations")
    resolved_output = (
        resolve_path(output_dir, config.project_root)
        if output_dir is not None
        else resolve_path(str(output_root), config.project_root) / config.dataset
    )
    resolved_alpha = float(alpha if alpha is not None else raw.setdefault("alpha", 0.45))
    if not 0.0 <= resolved_alpha <= 1.0:
        raise ConfigError("visualization alpha must be in [0, 1]")
    normalization = str(raw.setdefault("heatmap_normalization", "per_frame"))
    if normalization not in {"per_frame", "global"}:
        raise ConfigError("visualization.heatmap_normalization must be 'per_frame' or 'global'")
    image_format = str(raw.setdefault("image_format", "png")).lower().lstrip(".")
    if image_format not in {"png", "jpg", "jpeg"}:
        raise ConfigError("visualization.image_format must be png, jpg, or jpeg")
    return VisualizationSettings(
        output_dir=resolved_output,
        colormap=str(colormap if colormap is not None else raw.setdefault("colormap", "JET")),
        alpha=resolved_alpha,
        heatmap_normalization=normalization,
        draw_grid=bool(raw.setdefault("draw_grid", False)),
        draw_top_cells=bool(raw.setdefault("draw_top_cells", True)),
        top_cells_per_frame=int(raw.setdefault("top_cells_per_frame", 5)),
        top_frames=int(raw.setdefault("top_frames", 30)),
        min_score=float(min_score if min_score is not None else raw.setdefault("min_score", 0.70)),
        frame_source=str(raw.setdefault("frame_source", "preprocessed")),
        image_format=image_format,
        video_fps=float(raw.setdefault("video_fps", 10)),
    )


def _top_count(
    settings: VisualizationSettings,
    requested_top_frames: int | None,
    include_alerts: bool,
    video_id: str | None,
) -> int:
    if requested_top_frames is not None:
        return max(0, int(requested_top_frames))
    if include_alerts or video_id is not None:
        return 0
    return settings.top_frames


def _selection_from_score(score: FrameScore, selection_type: str, rank: int = 0) -> FrameSelection:
    return FrameSelection(
        dataset=score.dataset,
        video_id=score.video_id,
        frame_id=score.frame_id,
        frame_score=score.frame_score,
        smoothed_frame_score=score.smoothed_frame_score,
        severity=score.severity,
        top_cells=list(score.top_cells),
        selection_type=selection_type,
        rank=rank,
    )


def _default_video_id(frame_scores: list[FrameScore], alerts: list[dict[str, Any]]) -> str:
    if alerts:
        return str(max(alerts, key=lambda item: float(item.get("max_score", 0.0)))["video_id"])
    if not frame_scores:
        raise ConfigError("Cannot choose a default video because frame_scores.csv is empty")
    return max(frame_scores, key=lambda item: item.smoothed_frame_score).video_id


def _requests_by_video(keys: set[tuple[str, int]]) -> dict[str, set[int]]:
    requests: dict[str, set[int]] = {}
    for video_id, frame_id in keys:
        requests.setdefault(video_id, set()).add(frame_id)
    return requests


def _image_path(
    output_dir: Path,
    category: str,
    selection: FrameSelection,
    image_format: str,
) -> Path:
    ensure_dir(output_dir / category)
    score = f"{selection.smoothed_frame_score:.3f}"
    if selection.selection_type == "alert_peak":
        start = selection.alert_start_frame_id or selection.frame_id
        end = selection.alert_end_frame_id or selection.frame_id
        name = f"{selection.video_id}_{start:06d}_{end:06d}_peak.{image_format}"
    else:
        name = f"{selection.video_id}_{selection.frame_id:06d}_score_{score}.{image_format}"
    return output_dir / category / name


def _write_image(path: Path, image: np.ndarray) -> None:
    cv2 = _cv2()
    ensure_dir(path.parent)
    if not cv2.imwrite(str(path), image):
        raise ConfigError(f"Failed to write image: {path}")


def _write_video_overlay(
    config: AnomalyConfig,
    output_dir: Path,
    frame_batch: Any,
    cell_scores: dict[tuple[str, int], list[dict[str, Any]]],
    grid: GridSpec,
    selections: list[FrameSelection],
    settings: VisualizationSettings,
    global_max: float,
) -> dict[str, Any] | None:
    cv2 = _cv2()
    ensure_dir(output_dir / "videos")
    video_id = selections[0].video_id
    video_path = output_dir / "videos" / f"{video_id}_overlay.mp4"
    writer = None
    frames_written = 0
    try:
        for selection in selections:
            loaded_frame = frame_batch.frames.get((selection.video_id, selection.frame_id))
            if loaded_frame is None:
                continue
            overlay = render_overlay(
                frame_gray=loaded_frame.gray,
                score_rows=cell_scores.get((selection.video_id, selection.frame_id), []),
                grid=grid,
                top_cells=selection.top_cells[: settings.top_cells_per_frame],
                settings=settings,
                global_max=global_max,
            )
            if writer is None:
                height, width = overlay.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(str(video_path), fourcc, settings.video_fps, (width, height))
                if not writer.isOpened():
                    raise ConfigError(f"Cannot open video writer: {video_path}")
            writer.write(overlay)
            frames_written += 1
    finally:
        if writer is not None:
            writer.release()
    if frames_written == 0:
        return None
    return {
        "video_id": video_id,
        "video_path": _display_path(video_path, config.project_root),
        "relative_path": _relative_to(video_path, output_dir),
        "frames_written": frames_written,
        "fps": settings.video_fps,
    }


def _index_record(
    config: AnomalyConfig,
    output_dir: Path,
    image_path: Path,
    selection: FrameSelection,
) -> dict[str, Any]:
    return {
        "dataset": selection.dataset,
        "video_id": selection.video_id,
        "frame_id": selection.frame_id,
        "frame_score": selection.frame_score,
        "smoothed_frame_score": selection.smoothed_frame_score,
        "severity": selection.severity,
        "top_cells": selection.top_cells,
        "image_path": _display_path(image_path, config.project_root),
        "relative_path": _relative_to(image_path, output_dir),
        "selection_type": selection.selection_type,
        "rank": selection.rank,
        "alert_id": selection.alert_id,
        "reasons": selection.reasons,
    }


def _public_index(index_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(record) for record in index_records]


def _display_path(path: str | Path, project_root: str | Path) -> str:
    path_obj = Path(path).resolve()
    root = Path(project_root).resolve()
    try:
        return str(path_obj.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path_obj)


def _relative_to(path: str | Path, root: str | Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _parse_top_cells(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return [item.strip() for item in raw_value.split(",") if item.strip()]
    if isinstance(payload, list):
        return [str(item) for item in payload]
    return []


def _normalize_heatmap(heatmap: np.ndarray, mode: str, global_max: float) -> np.ndarray:
    heatmap = np.clip(heatmap.astype(np.float32), 0.0, 1.0)
    if mode == "per_frame":
        max_value = float(np.max(heatmap)) if heatmap.size else 0.0
        return heatmap / max_value if max_value > 0.0 else heatmap
    if mode == "global":
        scale = max(float(global_max), 1.0e-12)
        return np.clip(heatmap / scale, 0.0, 1.0)
    raise ConfigError(f"Unsupported heatmap normalization: {mode}")


def _draw_grid(image: np.ndarray, grid: GridSpec) -> None:
    cv2 = _cv2()
    for cell in grid.cells.values():
        cv2.rectangle(image, (cell.x1, cell.y1), (cell.x2 - 1, cell.y2 - 1), (80, 80, 80), 1)


def _draw_top_cells(
    image: np.ndarray,
    grid: GridSpec,
    top_cells: list[str],
    score_by_cell: dict[str, float],
) -> None:
    cv2 = _cv2()
    for index, cell_id in enumerate(top_cells):
        cell = grid.cells.get(cell_id)
        if cell is None:
            continue
        color = (0, 255, 255) if index == 0 else (0, 255, 0)
        cv2.rectangle(image, (cell.x1, cell.y1), (cell.x2 - 1, cell.y2 - 1), color, 2)
        label = f"{cell_id} {score_by_cell.get(cell_id, 0.0):.2f}"
        y = max(cell.y1 + 12, 12)
        cv2.putText(image, label, (cell.x1 + 2, y), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(image, label, (cell.x1 + 2, y), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 255), 1, cv2.LINE_AA)


def _colormap_id(name: str) -> int:
    cv2 = _cv2()
    attr = f"COLORMAP_{name.upper()}"
    if not hasattr(cv2, attr):
        raise ConfigError(f"Unknown OpenCV colormap: {name}")
    return int(getattr(cv2, attr))


def _cv2():
    try:
        import cv2
    except ImportError as exc:
        raise ConfigError(
            "OpenCV is required for visualization. "
            "Install dependencies with: python -m pip install -r src/requirements.txt"
        ) from exc
    return cv2
