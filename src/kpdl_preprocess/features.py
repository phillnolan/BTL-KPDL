from __future__ import annotations

import numpy as np

from .config import get_nested
from .records import CellRecord, FrameRecord
from .schema import feature_columns


def extract_cube_features(
    cube_id: str,
    cube: list[FrameRecord],
    cells: list[CellRecord],
    config: dict,
) -> list[dict[str, object]]:
    method = str(get_nested(config, "features", "motion_method", default="frame_diff"))
    if method != "frame_diff":
        raise ValueError("Only features.motion_method='frame_diff' is implemented in SPEC 1 baseline")

    threshold = float(get_nested(config, "features", "frame_diff_threshold", default=15))
    direction_bins = int(get_nested(config, "features", "direction_bins", default=8))

    frames = np.stack([frame.gray for frame in cube]).astype(np.float32)
    diffs = np.abs(np.diff(frames, axis=0))
    masks = diffs > threshold

    first = cube[0]
    last = cube[-1]
    center = cube[len(cube) // 2]

    rows: list[dict[str, object]] = []
    for cell in cells:
        y1, y2, x1, x2 = cell.y1, cell.y2, cell.x1, cell.x2
        cell_diffs = diffs[:, y1:y2, x1:x2]
        cell_masks = masks[:, y1:y2, x1:x2]
        center_crop = center.gray[y1:y2, x1:x2].astype(np.float32)
        first_crop = first.gray[y1:y2, x1:x2].astype(np.float32)
        last_crop = last.gray[y1:y2, x1:x2].astype(np.float32)

        foreground_ratio = _safe_mean(np.any(cell_masks, axis=0))
        motion_density = _safe_mean(cell_masks)
        motion_magnitude_mean = _safe_mean(cell_diffs)
        motion_magnitude_std = _safe_std(cell_diffs)
        brightness_mean = _safe_mean(center_crop)
        brightness_delta = _safe_mean(last_crop) - _safe_mean(first_crop)

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
        for bin_index in range(direction_bins):
            row[f"direction_hist_{bin_index}"] = 0.0
        rows.append(row)

    return rows


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
