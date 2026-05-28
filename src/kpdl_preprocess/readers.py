from __future__ import annotations

from pathlib import Path
from typing import Iterator

import numpy as np

from .config import ConfigError, get_nested
from .records import FrameRecord, VideoSource
from .utils import bool_config, sorted_natural, stem_to_frame_id


def _cv2():
    try:
        import cv2
    except ImportError as exc:
        raise ConfigError(
            "OpenCV is required for preprocessing. "
            "Install dependencies with: python -m pip install -r requirements.txt"
        ) from exc
    return cv2


def iter_preprocessed_frames(
    source: VideoSource,
    config: dict,
    limit_frames: int | None = None,
) -> Iterator[FrameRecord]:
    if source.input_type == "frame_sequence":
        yield from _iter_frame_sequence(source, config, limit_frames)
        return
    if source.input_type == "video":
        yield from _iter_video(source, config, limit_frames)
        return
    raise ConfigError(f"Unsupported source input_type: {source.input_type}")


def probe_video(source: VideoSource) -> dict:
    if source.input_type != "video":
        return {"fps": None, "num_frames_hint": None, "original_width": None, "original_height": None}

    cv2 = _cv2()
    cap = cv2.VideoCapture(str(source.source_path))
    if not cap.isOpened():
        return {"fps": None, "num_frames_hint": None, "original_width": None, "original_height": None}
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or None
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) or None
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) or None
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0) or None
        return {"fps": fps, "num_frames_hint": count, "original_width": width, "original_height": height}
    finally:
        cap.release()


def _iter_frame_sequence(
    source: VideoSource,
    config: dict,
    limit_frames: int | None,
) -> Iterator[FrameRecord]:
    cv2 = _cv2()
    files = sorted_natural(source.source_path.glob("*.tif"))
    if limit_frames is not None:
        files = files[:limit_frames]

    for index, image_path in enumerate(files, start=1):
        raw = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if raw is None:
            continue
        gray, original_width, original_height = preprocess_frame(raw, config)
        yield FrameRecord(
            dataset=source.dataset,
            split=source.split,
            video_id=source.video_id,
            frame_id=stem_to_frame_id(image_path, index),
            timestamp=float(index - 1),
            source_path=image_path,
            original_width=original_width,
            original_height=original_height,
            resized_width=gray.shape[1],
            resized_height=gray.shape[0],
            gray=gray,
        )


def _iter_video(
    source: VideoSource,
    config: dict,
    limit_frames: int | None,
) -> Iterator[FrameRecord]:
    cv2 = _cv2()
    cap = cv2.VideoCapture(str(source.source_path))
    if not cap.isOpened():
        raise ConfigError(f"Cannot open video: {source.source_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count_hint = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) or None
    safety_limit = _video_safety_limit(frame_count_hint, limit_frames)
    frame_index = 0
    try:
        while True:
            if limit_frames is not None and frame_index >= limit_frames:
                break
            if safety_limit is not None and frame_index >= safety_limit:
                break
            ok, raw = cap.read()
            if not ok:
                break
            frame_index += 1
            gray, original_width, original_height = preprocess_frame(raw, config)
            timestamp = (frame_index / fps) if fps > 0 else None
            yield FrameRecord(
                dataset=source.dataset,
                split=source.split,
                video_id=source.video_id,
                frame_id=frame_index,
                timestamp=timestamp,
                source_path=source.source_path,
                original_width=original_width,
                original_height=original_height,
                resized_width=gray.shape[1],
                resized_height=gray.shape[0],
                gray=gray,
            )
    finally:
        cap.release()


def preprocess_frame(raw: np.ndarray, config: dict) -> tuple[np.ndarray, int, int]:
    cv2 = _cv2()
    resize_width = int(get_nested(config, "video", "resize_width"))
    resize_height = int(get_nested(config, "video", "resize_height"))

    original_height, original_width = raw.shape[:2]
    resized = cv2.resize(raw, (resize_width, resize_height), interpolation=cv2.INTER_AREA)

    if resized.ndim == 2:
        gray = resized
    elif resized.shape[2] == 4:
        gray = cv2.cvtColor(resized, cv2.COLOR_BGRA2GRAY)
    else:
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    if gray.dtype != np.uint8:
        gray = np.clip(gray, 0, 255).astype(np.uint8)

    if bool_config(get_nested(config, "video", "blur", "enabled"), default=False):
        kernel_size = int(get_nested(config, "video", "blur", "kernel_size", default=3))
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel_size = max(kernel_size, 1)
        if kernel_size > 1:
            gray = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)

    if bool_config(get_nested(config, "video", "brightness_normalization", "enabled"), default=False):
        gray = cv2.equalizeHist(gray)

    return gray, original_width, original_height


def _video_safety_limit(frame_count_hint: int | None, limit_frames: int | None) -> int | None:
    if frame_count_hint is None or frame_count_hint <= 0:
        return limit_frames
    tolerance = max(100, int(frame_count_hint * 0.05))
    guarded_limit = frame_count_hint + tolerance
    return min(guarded_limit, limit_frames) if limit_frames is not None else guarded_limit
