from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kpdl_preprocess.config import ConfigError, copy_config, get_nested, load_config, resolve_path

from .schema import DEFAULT_FEATURE_COLUMNS


@dataclass(frozen=True)
class AnomalyConfig:
    raw: dict[str, Any]
    config_path: Path
    project_root: Path
    dataset: str
    preprocessed_dir: Path
    train_feature_path: Path
    test_feature_path: Path
    grid_path: Path
    preprocess_stats_path: Path
    model_root: Path
    result_root: Path
    model_dir: Path
    result_dir: Path
    model_type: str
    clusters_per_cell: int
    min_samples_per_cell: int
    batch_size: int
    max_iter: int
    random_state: int
    threshold_percentile: float
    threshold_floor: float
    feature_columns: list[str]
    cluster_weight: float
    temporal_weight: float
    top_k_cells: int
    smoothing_window: int
    alert_threshold_medium: float
    alert_threshold_high: float
    min_consecutive_alerts: int


def load_anomaly_config(
    config_path: str | Path,
    project_root: str | Path = ".",
    model_root: str | Path | None = None,
    result_root: str | Path | None = None,
    clusters_per_cell: int | None = None,
    threshold_percentile: float | None = None,
) -> AnomalyConfig:
    config_path = Path(config_path)
    project_root = Path(project_root).resolve()
    raw = copy_config(load_config(config_path))

    model = raw.setdefault("model", {})
    model.setdefault("type", "minibatch_kmeans")
    model.setdefault("clusters_per_cell", 5)
    model.setdefault("min_samples_per_cell", 50)
    model.setdefault("batch_size", 1024)
    model.setdefault("max_iter", 200)
    model.setdefault("random_state", 10)
    model.setdefault("threshold_percentile", 99.0)
    model.setdefault("threshold_floor", 1.0e-9)
    if clusters_per_cell is not None:
        model["clusters_per_cell"] = clusters_per_cell
    if threshold_percentile is not None:
        model["threshold_percentile"] = threshold_percentile

    scoring = raw.setdefault("scoring", {})
    scoring.setdefault("feature_columns", list(DEFAULT_FEATURE_COLUMNS))
    scoring.setdefault("cluster_weight", 0.80)
    scoring.setdefault("temporal_weight", 0.20)
    scoring.setdefault("top_k_cells", 5)
    scoring.setdefault("smoothing_window", 5)
    scoring.setdefault("alert_threshold_medium", 0.70)
    scoring.setdefault("alert_threshold_high", 0.90)
    scoring.setdefault("min_consecutive_alerts", 3)

    output = raw.setdefault("output", {})
    output.setdefault("root", "src/outputs/preprocessed")
    output.setdefault("model_root", "src/outputs/models")
    output.setdefault("result_root", "src/outputs/results")
    if model_root is not None:
        output["model_root"] = str(model_root)
    if result_root is not None:
        output["result_root"] = str(result_root)

    dataset = str(get_nested(raw, "data", "dataset"))
    preprocessed_root = resolve_path(str(get_nested(raw, "output", "root")), project_root)
    model_root_path = resolve_path(str(get_nested(raw, "output", "model_root")), project_root)
    result_root_path = resolve_path(str(get_nested(raw, "output", "result_root")), project_root)
    preprocessed_dir = preprocessed_root / dataset

    feature_columns = list(get_nested(raw, "scoring", "feature_columns", default=DEFAULT_FEATURE_COLUMNS))
    if not feature_columns or not all(isinstance(column, str) for column in feature_columns):
        raise ConfigError("scoring.feature_columns must be a non-empty list of strings")

    model_type = str(get_nested(raw, "model", "type"))
    if model_type != "minibatch_kmeans":
        raise ConfigError("SPEC 3 currently supports only model.type='minibatch_kmeans'")

    clusters = _positive_int(raw, "model", "clusters_per_cell")
    min_samples = _positive_int(raw, "model", "min_samples_per_cell")
    batch_size = _positive_int(raw, "model", "batch_size")
    max_iter = _positive_int(raw, "model", "max_iter")
    random_state = int(get_nested(raw, "model", "random_state", default=10))
    percentile = float(get_nested(raw, "model", "threshold_percentile", default=99.0))
    if percentile <= 0.0 or percentile > 100.0:
        raise ConfigError("model.threshold_percentile must be in the interval (0, 100]")
    threshold_floor = float(get_nested(raw, "model", "threshold_floor", default=1.0e-9))
    if threshold_floor < 0.0:
        raise ConfigError("model.threshold_floor must be non-negative")

    cluster_weight = float(get_nested(raw, "scoring", "cluster_weight", default=0.80))
    temporal_weight = float(get_nested(raw, "scoring", "temporal_weight", default=0.20))
    if cluster_weight < 0.0 or temporal_weight < 0.0:
        raise ConfigError("scoring weights must be non-negative")

    medium = float(get_nested(raw, "scoring", "alert_threshold_medium", default=0.70))
    high = float(get_nested(raw, "scoring", "alert_threshold_high", default=0.90))
    if not 0.0 <= medium <= high <= 1.0:
        raise ConfigError("alert thresholds must satisfy 0 <= medium <= high <= 1")

    return AnomalyConfig(
        raw=raw,
        config_path=config_path,
        project_root=project_root,
        dataset=dataset,
        preprocessed_dir=preprocessed_dir,
        train_feature_path=preprocessed_dir / "features_train.csv",
        test_feature_path=preprocessed_dir / "features_test.csv",
        grid_path=preprocessed_dir / "grid.json",
        preprocess_stats_path=preprocessed_dir / "preprocess_stats.json",
        model_root=model_root_path,
        result_root=result_root_path,
        model_dir=model_root_path / dataset,
        result_dir=result_root_path / dataset,
        model_type=model_type,
        clusters_per_cell=clusters,
        min_samples_per_cell=min_samples,
        batch_size=batch_size,
        max_iter=max_iter,
        random_state=random_state,
        threshold_percentile=percentile,
        threshold_floor=threshold_floor,
        feature_columns=feature_columns,
        cluster_weight=cluster_weight,
        temporal_weight=temporal_weight,
        top_k_cells=_positive_int(raw, "scoring", "top_k_cells"),
        smoothing_window=_positive_int(raw, "scoring", "smoothing_window"),
        alert_threshold_medium=medium,
        alert_threshold_high=high,
        min_consecutive_alerts=_positive_int(raw, "scoring", "min_consecutive_alerts"),
    )


def _positive_int(config: dict[str, Any], section: str, key: str) -> int:
    value = int(get_nested(config, section, key))
    if value <= 0:
        raise ConfigError(f"{section}.{key} must be a positive integer")
    return value
