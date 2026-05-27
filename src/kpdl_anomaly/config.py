from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kpdl_preprocess.config import ConfigError, copy_config, get_nested, load_config, resolve_path

from .schema import DEFAULT_FEATURE_COLUMNS


@dataclass(frozen=True)
class RulesConfig:
    enabled: bool
    output_root: Path
    model_dir: Path | None
    algorithm: str
    min_support: float
    min_confidence: float
    min_lift: float
    max_itemset_size: int
    max_rules: int
    include_cell_token: bool
    include_cluster_token: bool
    include_brightness_token: bool
    include_direction_token: bool
    rare_itemset_size: int
    rare_support_floor: float
    rare_score_cap: float


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
    rare_token_weight: float
    rule_weight: float
    top_k_cells: int
    smoothing_window: int
    alert_threshold_medium: float
    alert_threshold_high: float
    min_consecutive_alerts: int
    rules: RulesConfig


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

    rules = raw.setdefault("rules", {})
    rules.setdefault("enabled", False)
    rules.setdefault("output_root", "src/outputs/rules")
    rules.setdefault("model_dir", None)
    rules.setdefault("algorithm", "bounded_apriori")
    rules.setdefault("min_support", 0.01)
    rules.setdefault("min_confidence", 0.60)
    rules.setdefault("min_lift", 1.05)
    rules.setdefault("max_itemset_size", 3)
    rules.setdefault("max_rules", 200)
    rules.setdefault("include_cell_token", True)
    rules.setdefault("include_cluster_token", True)
    rules.setdefault("include_brightness_token", True)
    rules.setdefault("include_direction_token", False)
    rules.setdefault("rare_itemset_size", 3)
    rules.setdefault("rare_support_floor", 0.001)
    rules.setdefault("rare_score_cap", 1.0)

    scoring = raw.setdefault("scoring", {})
    rules_enabled = bool(get_nested(raw, "rules", "enabled", default=False))
    scoring.setdefault("feature_columns", list(DEFAULT_FEATURE_COLUMNS))
    scoring.setdefault("cluster_weight", 0.65 if rules_enabled else 0.80)
    scoring.setdefault("temporal_weight", 0.20)
    scoring.setdefault("rare_token_weight", 0.10 if rules_enabled else 0.0)
    scoring.setdefault("rule_weight", 0.05 if rules_enabled else 0.0)
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
    rule_output_root = resolve_path(str(get_nested(raw, "rules", "output_root")), project_root)
    rule_model_dir_value = get_nested(raw, "rules", "model_dir", default=None)
    rule_model_dir = (
        resolve_path(str(rule_model_dir_value), project_root)
        if rule_model_dir_value not in {None, ""}
        else None
    )
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
    rare_token_weight = float(get_nested(raw, "scoring", "rare_token_weight", default=0.0))
    rule_weight = float(get_nested(raw, "scoring", "rule_weight", default=0.0))
    if cluster_weight < 0.0 or temporal_weight < 0.0 or rare_token_weight < 0.0 or rule_weight < 0.0:
        raise ConfigError("scoring weights must be non-negative")

    medium = float(get_nested(raw, "scoring", "alert_threshold_medium", default=0.70))
    high = float(get_nested(raw, "scoring", "alert_threshold_high", default=0.90))
    if not 0.0 <= medium <= high <= 1.0:
        raise ConfigError("alert thresholds must satisfy 0 <= medium <= high <= 1")

    algorithm = str(get_nested(raw, "rules", "algorithm", default="bounded_apriori"))
    if algorithm != "bounded_apriori":
        raise ConfigError("rules.algorithm currently supports only 'bounded_apriori'")
    min_support = _probability(raw, "rules", "min_support", allow_zero=False)
    min_confidence = _probability(raw, "rules", "min_confidence", allow_zero=False)
    min_lift = float(get_nested(raw, "rules", "min_lift", default=1.05))
    if min_lift <= 0.0:
        raise ConfigError("rules.min_lift must be positive")
    rare_support_floor = _probability(raw, "rules", "rare_support_floor", allow_zero=True)
    rare_score_cap = _probability(raw, "rules", "rare_score_cap", allow_zero=True)

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
        rare_token_weight=rare_token_weight,
        rule_weight=rule_weight,
        top_k_cells=_positive_int(raw, "scoring", "top_k_cells"),
        smoothing_window=_positive_int(raw, "scoring", "smoothing_window"),
        alert_threshold_medium=medium,
        alert_threshold_high=high,
        min_consecutive_alerts=_positive_int(raw, "scoring", "min_consecutive_alerts"),
        rules=RulesConfig(
            enabled=rules_enabled,
            output_root=rule_output_root,
            model_dir=rule_model_dir,
            algorithm=algorithm,
            min_support=min_support,
            min_confidence=min_confidence,
            min_lift=min_lift,
            max_itemset_size=_positive_int(raw, "rules", "max_itemset_size"),
            max_rules=_positive_int(raw, "rules", "max_rules"),
            include_cell_token=bool(get_nested(raw, "rules", "include_cell_token", default=True)),
            include_cluster_token=bool(get_nested(raw, "rules", "include_cluster_token", default=True)),
            include_brightness_token=bool(get_nested(raw, "rules", "include_brightness_token", default=True)),
            include_direction_token=bool(get_nested(raw, "rules", "include_direction_token", default=False)),
            rare_itemset_size=_positive_int(raw, "rules", "rare_itemset_size"),
            rare_support_floor=rare_support_floor,
            rare_score_cap=rare_score_cap,
        ),
    )


def _positive_int(config: dict[str, Any], section: str, key: str) -> int:
    value = int(get_nested(config, section, key))
    if value <= 0:
        raise ConfigError(f"{section}.{key} must be a positive integer")
    return value


def _probability(config: dict[str, Any], section: str, key: str, allow_zero: bool) -> float:
    value = float(get_nested(config, section, key))
    lower_ok = value >= 0.0 if allow_zero else value > 0.0
    if not lower_ok or value > 1.0:
        bound = "[0, 1]" if allow_zero else "(0, 1]"
        raise ConfigError(f"{section}.{key} must be in the interval {bound}")
    return value
