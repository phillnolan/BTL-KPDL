from __future__ import annotations

SCHEMA_VERSION = "spec_3.anomaly.v1"

METADATA_COLUMNS = [
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
]

DEFAULT_FEATURE_COLUMNS = [
    "foreground_ratio",
    "motion_magnitude_mean",
    "motion_magnitude_std",
    "motion_density",
    "brightness_mean",
    "brightness_delta",
]

CELL_SCORE_COLUMNS = [
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
    "nearest_cluster",
    "cluster_distance",
    "cluster_threshold",
    "cluster_distance_score",
    "temporal_change_score",
    "cell_score",
]

FRAME_SCORE_COLUMNS = [
    "dataset",
    "split",
    "video_id",
    "frame_id",
    "frame_score",
    "smoothed_frame_score",
    "severity",
    "top_cells",
]
