from __future__ import annotations

SCHEMA_VERSION = "spec_7.common.v1"

FRAME_MANIFEST_COLUMNS = [
    "dataset",
    "split",
    "video_id",
    "frame_id",
    "timestamp",
    "source_path",
    "original_width",
    "original_height",
    "resized_width",
    "resized_height",
]

VIDEO_MANIFEST_COLUMNS = [
    "dataset",
    "split",
    "video_id",
    "source_path",
    "input_type",
    "fps",
    "num_frames",
    "num_cubes",
    "original_width",
    "original_height",
    "failed",
    "error",
]

BASE_FEATURE_COLUMNS = [
    "dataset",
    "split",
    "video_id",
    "cube_id",
    "start_frame_id",
    "end_frame_id",
    "center_frame_id",
    "cell_id",
    "cell_row",
    "cell_col",
    "foreground_ratio",
    "motion_magnitude_mean",
    "motion_magnitude_std",
    "motion_density",
]

TAIL_FEATURE_COLUMNS = [
    "brightness_mean",
    "brightness_delta",
]


def feature_columns(direction_bins: int = 8) -> list[str]:
    return (
        BASE_FEATURE_COLUMNS
        + [f"direction_hist_{index}" for index in range(direction_bins)]
        + TAIL_FEATURE_COLUMNS
    )
