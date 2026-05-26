from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from kpdl_preprocess.config import ConfigError
from kpdl_preprocess.datasets import scan_dataset
from kpdl_preprocess.readers import iter_preprocessed_frames

from .config import AnomalyConfig


@dataclass(frozen=True)
class LoadedFrame:
    video_id: str
    frame_id: int
    gray: np.ndarray
    source_path: Path
    resized_width: int
    resized_height: int


@dataclass(frozen=True)
class FrameBatch:
    frames: dict[tuple[str, int], LoadedFrame]
    missing: list[dict[str, object]]


def load_preprocessed_frames(
    config: AnomalyConfig,
    frame_requests: dict[str, set[int]],
) -> FrameBatch:
    """Read resized grayscale test frames requested by video/frame id."""
    if not frame_requests:
        return FrameBatch(frames={}, missing=[])

    sources = {
        source.video_id: source
        for source in scan_dataset(config.raw, config.project_root, split_filter="test")
    }
    loaded: dict[tuple[str, int], LoadedFrame] = {}
    missing: list[dict[str, object]] = []

    for video_id, requested_ids in sorted(frame_requests.items()):
        requested = {int(frame_id) for frame_id in requested_ids}
        if not requested:
            continue

        source = sources.get(video_id)
        if source is None:
            for frame_id in sorted(requested):
                missing.append(
                    {
                        "video_id": video_id,
                        "frame_id": frame_id,
                        "reason": "video_source_not_found",
                    }
                )
            continue

        max_requested = max(requested)
        remaining = set(requested)
        for record in iter_preprocessed_frames(source, config.raw):
            frame_id = int(record.frame_id)
            if frame_id in remaining:
                loaded[(video_id, frame_id)] = LoadedFrame(
                    video_id=video_id,
                    frame_id=frame_id,
                    gray=record.gray,
                    source_path=record.source_path,
                    resized_width=int(record.resized_width),
                    resized_height=int(record.resized_height),
                )
                remaining.remove(frame_id)
                if not remaining:
                    break
            if frame_id > max_requested and source.input_type in {"frame_sequence", "video"}:
                break

        for frame_id in sorted(remaining):
            missing.append(
                {
                    "video_id": video_id,
                    "frame_id": frame_id,
                    "reason": "frame_not_found",
                }
            )

    return FrameBatch(frames=loaded, missing=missing)


def ensure_preprocessed_frame_source(frame_source: str) -> None:
    if frame_source != "preprocessed":
        raise ConfigError(
            "SPEC 4 MVP currently supports visualization.frame_source='preprocessed' only"
        )
