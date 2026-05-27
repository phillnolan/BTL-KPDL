from __future__ import annotations

import numpy as np

from .config import ConfigError, get_nested
from .records import CellRecord, FrameRecord


def extract_cube_features(
    cube_id: str,
    cube: list[FrameRecord],
    cells: list[CellRecord],
    config: dict,
) -> list[dict[str, object]]:
    method = str(get_nested(config, "features", "motion_method", default="frame_diff")).lower()
    direction_bins = int(get_nested(config, "features", "direction_bins", default=8))
    frames = np.stack([frame.gray for frame in cube]).astype(np.float32)

    if method in {"frame_diff", "frame_difference"}:
        threshold = float(get_nested(config, "features", "frame_diff_threshold", default=15))
        motion_values = np.abs(np.diff(frames, axis=0))
        motion_masks = motion_values > threshold
        direction_angles = None
    elif method in {"farneback", "optical_flow", "flow"}:
        threshold = float(get_nested(config, "features", "flow_magnitude_threshold", default=0.2))
        motion_values, direction_angles = _farneback_motion(frames, config)
        motion_masks = motion_values > threshold
    else:
        raise ConfigError(
            "features.motion_method must be one of: frame_diff, farneback, optical_flow"
        )

    first = cube[0]
    last = cube[-1]
    center = cube[len(cube) // 2]

    rows: list[dict[str, object]] = []
    for cell in cells:
        y1, y2, x1, x2 = cell.y1, cell.y2, cell.x1, cell.x2
        cell_motion = motion_values[:, y1:y2, x1:x2]
        cell_masks = motion_masks[:, y1:y2, x1:x2]
        center_crop = center.gray[y1:y2, x1:x2].astype(np.float32)
        first_crop = first.gray[y1:y2, x1:x2].astype(np.float32)
        last_crop = last.gray[y1:y2, x1:x2].astype(np.float32)

        foreground_ratio = _safe_mean(np.any(cell_masks, axis=0))
        motion_density = _safe_mean(cell_masks)
        motion_magnitude_mean = _safe_mean(cell_motion)
        motion_magnitude_std = _safe_std(cell_motion)
        brightness_mean = _safe_mean(center_crop)
        brightness_delta = _safe_mean(last_crop) - _safe_mean(first_crop)
        direction_hist = _cell_direction_histogram(
            angles=None if direction_angles is None else direction_angles[:, y1:y2, x1:x2],
            magnitudes=cell_motion,
            mask=cell_masks,
            bins=direction_bins,
        )

        row: dict[str, object] = {
            "dataset": first.dataset,
            "split": first.split,
            "video_id": first.video_id,
            "cube_id": cube_id,
            "start_frame_id": first.frame_id,
            "end_frame_id": last.frame_id,
            "center_frame_id": center.frame_id,
            "cell_id": cell.cell_id,
            "cell_row": cell.row,
            "cell_col": cell.col,
            "foreground_ratio": foreground_ratio,
            "motion_magnitude_mean": motion_magnitude_mean,
            "motion_magnitude_std": motion_magnitude_std,
            "motion_density": motion_density,
            "brightness_mean": brightness_mean,
            "brightness_delta": brightness_delta,
        }
        for bin_index, hist_value in enumerate(direction_hist):
            row[f"direction_hist_{bin_index}"] = hist_value
        rows.append(row)

    return rows


def _farneback_motion(frames: np.ndarray, config: dict) -> tuple[np.ndarray, np.ndarray]:
    try:
        import cv2
    except ImportError as exc:
        raise ConfigError(
            "OpenCV is required for Farneback optical flow. "
            "Install dependencies with: python -m pip install -r src/requirements.txt"
        ) from exc

    params = dict(get_nested(config, "features", "farneback", default={}) or {})
    pyr_scale = float(params.get("pyr_scale", 0.5))
    levels = int(params.get("levels", 3))
    winsize = int(params.get("winsize", 15))
    iterations = int(params.get("iterations", 3))
    poly_n = int(params.get("poly_n", 5))
    poly_sigma = float(params.get("poly_sigma", 1.2))
    flags = int(params.get("flags", 0))

    gray_frames = np.clip(frames, 0, 255).astype(np.uint8)
    magnitudes: list[np.ndarray] = []
    angles: list[np.ndarray] = []
    for index in range(1, gray_frames.shape[0]):
        flow = cv2.calcOpticalFlowFarneback(
            gray_frames[index - 1],
            gray_frames[index],
            None,
            pyr_scale,
            levels,
            winsize,
            iterations,
            poly_n,
            poly_sigma,
            flags,
        )
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1], angleInDegrees=False)
        magnitudes.append(magnitude.astype(np.float32))
        angles.append(angle.astype(np.float32))

    if not magnitudes:
        empty_shape = (0, frames.shape[1], frames.shape[2])
        return np.zeros(empty_shape, dtype=np.float32), np.zeros(empty_shape, dtype=np.float32)
    return np.stack(magnitudes), np.stack(angles)


def _cell_direction_histogram(
    angles: np.ndarray | None,
    magnitudes: np.ndarray,
    mask: np.ndarray,
    bins: int,
) -> list[float]:
    if bins <= 0:
        return []
    if angles is None or angles.size == 0:
        return [0.0 for _ in range(bins)]

    moving = mask & np.isfinite(angles) & np.isfinite(magnitudes)
    if not np.any(moving):
        return [0.0 for _ in range(bins)]

    moving_angles = np.mod(angles[moving], 2.0 * np.pi)
    weights = magnitudes[moving].astype(np.float64)
    total_weight = float(np.sum(weights))
    if total_weight <= 1.0e-12:
        return [0.0 for _ in range(bins)]

    bin_indices = np.floor(moving_angles / (2.0 * np.pi) * bins).astype(np.int64)
    bin_indices = np.clip(bin_indices, 0, bins - 1)
    hist = np.bincount(bin_indices, weights=weights, minlength=bins).astype(np.float64)
    hist /= float(np.sum(hist))
    return [float(value) for value in hist]


def _safe_mean(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    result = float(np.mean(values))
    return result if np.isfinite(result) else 0.0


def _safe_std(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    result = float(np.std(values))
    return result if np.isfinite(result) else 0.0
