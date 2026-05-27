from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np

from kpdl_preprocess.config import ConfigError
from kpdl_preprocess.utils import ensure_dir

from .config import AnomalyConfig
from .io import read_json, require_files, write_json
from .schema import SCHEMA_VERSION
from .tokenization import row_to_tokens

ANALYSIS_SCHEMA_VERSION = "spec_9.analysis.v1"
MARKDOWN_ROW_LIMIT = 200
SUMMARY_TOKEN_PREFIXES = ("motion", "density", "brightness", "brightness_delta", "direction")


@dataclass(frozen=True)
class TokenContext:
    bins: Mapping[str, Any]
    include_cell_token: bool
    include_cluster_token: bool
    include_brightness_token: bool
    include_direction_token: bool
    source_dir: Path


def generate_cluster_profiles(
    config: AnomalyConfig,
    model_dir: str | Path,
    output_dir: str | Path,
    rules_dir: str | Path | None = None,
    use_rules: bool = True,
) -> dict[str, Any]:
    model_path = Path(model_dir)
    output_path = ensure_dir(output_dir)
    require_files(
        [
            model_path / "model_manifest.json",
            model_path / "cell_models.joblib",
            model_path / "cell_scalers.joblib",
            model_path / "thresholds.json",
        ]
    )

    warnings: list[str] = []
    model_manifest = read_json(model_path / "model_manifest.json")
    _validate_model_manifest(config, model_manifest)
    thresholds_payload = read_json(model_path / "thresholds.json")
    thresholds = dict(thresholds_payload.get("cells", {}))
    feature_stats = _read_optional_json(model_path / "feature_stats.json", warnings)
    models = joblib.load(model_path / "cell_models.joblib")
    scalers = joblib.load(model_path / "cell_scalers.joblib")
    token_context = _load_token_context(config, rules_dir, use_rules, warnings)

    cells: list[dict[str, Any]] = []
    for cell_id in sorted(thresholds.keys() | set(models.keys())):
        threshold_info = dict(thresholds.get(cell_id, {}))
        model = models.get(cell_id)
        scaler = scalers.get(cell_id)
        model_status = str(threshold_info.get("model_status", "trained" if model is not None else "missing_model"))
        cell_record = _cell_record(cell_id, threshold_info, model_status)
        if model is None or scaler is None:
            cell_record["clusters"] = []
            warnings.append(f"cell {cell_id} has no model/scaler; cluster profiles skipped")
            cells.append(cell_record)
            continue

        centers = _inverse_centers(cell_id, model, scaler, warnings)
        clusters: list[dict[str, Any]] = []
        for cluster_index, centroid in enumerate(centers):
            clusters.append(
                _cluster_record(
                    config=config,
                    cell_id=cell_id,
                    cluster_index=cluster_index,
                    centroid=centroid,
                    threshold_info=threshold_info,
                    token_context=token_context,
                )
            )
        cell_record["clusters"] = clusters
        cells.append(cell_record)

    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "source_schema_version": SCHEMA_VERSION,
        "dataset": config.dataset,
        "generated_at": generated_at,
        "config_path": str(config.config_path),
        "model_dir": str(model_path),
        "rules_dir": str(token_context.source_dir) if token_context is not None else None,
        "feature_columns": list(model_manifest.get("feature_columns", config.feature_columns)),
        "model_trained_at": model_manifest.get("trained_at"),
        "threshold_percentile": thresholds_payload.get("threshold_percentile"),
        "num_cells": len(cells),
        "num_clusters": sum(len(cell.get("clusters", [])) for cell in cells),
        "feature_stats_available": bool(feature_stats),
        "cells": cells,
        "warnings": _dedupe(warnings),
    }
    write_json(output_path / "cluster_profiles.json", payload)
    write_cluster_profiles_markdown(output_path / "cluster_profiles.md", payload)
    return payload


def write_cluster_profiles_markdown(path: str | Path, payload: Mapping[str, Any]) -> None:
    clusters = list(_iter_cluster_rows(payload))
    shown = clusters[:MARKDOWN_ROW_LIMIT]
    lines = [
        f"# Cluster Profiles - {payload.get('dataset')}",
        "",
        f"Generated at: `{payload.get('generated_at')}`",
        f"Model dir: `{payload.get('model_dir')}`",
        f"Clusters in JSON: `{payload.get('num_clusters', len(clusters))}`",
        f"Rows shown here: `{len(shown)}` of `{len(clusters)}`",
        "",
    ]
    warnings = list(payload.get("warnings", []))
    if warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")

    lines.extend(
        [
            "## Cluster Table",
            "",
            "| Cell | Cluster | Support | Motion | Density | Brightness | Direction | Threshold | Notes |",
            "| --- | --- | ---: | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    if not shown:
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | No trained clusters. |")
    for item in shown:
        tokens = item["token_map"]
        support = item["support"]
        support_text = "" if support is None else f"{support:.4f}"
        threshold = item["threshold"]
        threshold_text = "" if threshold is None else f"{threshold:.4f}"
        lines.append(
            "| {cell} | {cluster} | {support} | {motion} | {density} | {brightness} | {direction} | {threshold} | {summary} |".format(
                cell=item["cell_id"],
                cluster=item["cluster_id"],
                support=support_text,
                motion=tokens.get("motion", ""),
                density=tokens.get("density", ""),
                brightness=tokens.get("brightness", ""),
                direction=tokens.get("direction", ""),
                threshold=threshold_text,
                summary=item["summary"],
            )
        )
    lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _read_optional_json(path: Path, warnings: list[str]) -> dict[str, Any]:
    if not path.exists():
        warnings.append(f"optional artifact missing: {path}")
        return {}
    payload = read_json(path)
    return dict(payload) if isinstance(payload, dict) else {}


def _load_token_context(
    config: AnomalyConfig,
    rules_dir: str | Path | None,
    use_rules: bool,
    warnings: list[str],
) -> TokenContext | None:
    if not use_rules:
        warnings.append("token interpretation skipped because rules were disabled for this run")
        return None

    rule_path = Path(rules_dir) if rules_dir is not None else config.rules.output_root / config.dataset
    manifest_path = rule_path / "rule_manifest.json"
    bins_path = rule_path / "token_bins.json"
    if not manifest_path.exists() or not bins_path.exists():
        warnings.append(f"token interpretation unavailable; missing {manifest_path} or {bins_path}")
        return None

    manifest = read_json(manifest_path)
    if manifest.get("dataset") != config.dataset:
        warnings.append(
            f"token interpretation skipped because rule dataset={manifest.get('dataset')!r} "
            f"does not match config dataset={config.dataset!r}"
        )
        return None
    if list(manifest.get("feature_columns", [])) != config.feature_columns:
        warnings.append("token interpretation skipped because rule feature_columns do not match config")
        return None

    token_schema = dict(manifest.get("token_schema", {}))
    return TokenContext(
        bins=read_json(bins_path),
        include_cell_token=bool(token_schema.get("include_cell_token", True)),
        include_cluster_token=bool(token_schema.get("include_cluster_token", True)),
        include_brightness_token=bool(token_schema.get("include_brightness_token", True)),
        include_direction_token=bool(token_schema.get("include_direction_token", False)),
        source_dir=rule_path,
    )


def _validate_model_manifest(config: AnomalyConfig, manifest: Mapping[str, Any]) -> None:
    if manifest.get("dataset") != config.dataset:
        raise ConfigError(f"model dataset={manifest.get('dataset')!r} does not match config dataset={config.dataset!r}")
    if list(manifest.get("feature_columns", [])) != config.feature_columns:
        raise ConfigError("model feature_columns do not match config scoring.feature_columns")


def _cell_record(cell_id: str, threshold_info: Mapping[str, Any], model_status: str) -> dict[str, Any]:
    return {
        "cell_id": cell_id,
        "model_status": model_status,
        "threshold": _float_or_none(threshold_info.get("threshold")),
        "distance_mean": _float_or_none(threshold_info.get("distance_mean")),
        "distance_std": _float_or_none(threshold_info.get("distance_std")),
        "distance_p95": _float_or_none(threshold_info.get("distance_p95")),
        "distance_p99": _float_or_none(threshold_info.get("distance_p99")),
        "num_train_samples": _int_or_none(threshold_info.get("num_train_samples")),
    }


def _inverse_centers(cell_id: str, model: Any, scaler: Any, warnings: list[str]) -> np.ndarray:
    centers = np.asarray(getattr(model, "cluster_centers_", []), dtype=np.float64)
    if centers.ndim != 2:
        warnings.append(f"cell {cell_id} has invalid cluster center shape; no centroids written")
        return np.empty((0, 0), dtype=np.float64)
    try:
        return np.asarray(scaler.inverse_transform(centers), dtype=np.float64)
    except (AttributeError, ValueError) as exc:
        warnings.append(f"cell {cell_id} centroid inverse_transform failed: {exc}")
        return centers


def _cluster_record(
    config: AnomalyConfig,
    cell_id: str,
    cluster_index: int,
    centroid: np.ndarray,
    threshold_info: Mapping[str, Any],
    token_context: TokenContext | None,
) -> dict[str, Any]:
    cluster_id = f"C{cluster_index}"
    centroid_by_feature = {
        feature: _float_or_none(centroid[index]) if index < len(centroid) else None
        for index, feature in enumerate(config.feature_columns)
    }
    tokens: list[str] = []
    interpretation_status = "insufficient_token_bins"
    if token_context is not None:
        row = _centroid_row(cell_id, centroid_by_feature)
        tokens = row_to_tokens(
            row,
            token_context.bins,
            cluster_index,
            include_cell_token=token_context.include_cell_token,
            include_cluster_token=token_context.include_cluster_token,
            include_brightness_token=token_context.include_brightness_token,
            include_direction_token=token_context.include_direction_token,
        )
        interpretation_status = "interpreted"

    token_summary = _token_map(tokens)
    support_count, support = _cluster_support(cluster_index, threshold_info)
    summary = _cluster_summary(cell_id, cluster_id, token_summary, interpretation_status)
    return {
        "cluster_id": cluster_id,
        "centroid": centroid_by_feature,
        "tokens": tokens,
        "token_summary": token_summary,
        "interpretation_status": interpretation_status,
        "support_count": support_count,
        "support": support,
        "summary": summary,
    }


def _centroid_row(cell_id: str, centroid_by_feature: Mapping[str, float | None]) -> dict[str, Any]:
    row: dict[str, Any] = {feature: value for feature, value in centroid_by_feature.items() if value is not None}
    parsed = _parse_cell_id(cell_id)
    row["cell_id"] = cell_id
    if parsed is not None:
        row["cell_row"] = parsed[0]
        row["cell_col"] = parsed[1]
    return row


def _cluster_support(cluster_index: int, threshold_info: Mapping[str, Any]) -> tuple[int | None, float | None]:
    sizes = list(threshold_info.get("cluster_sizes", []))
    sample_count = _int_or_none(threshold_info.get("num_train_samples"))
    if cluster_index >= len(sizes) or sample_count is None or sample_count <= 0:
        return None, None
    count = _int_or_none(sizes[cluster_index])
    if count is None:
        return None, None
    return count, _clip_probability(count / sample_count)


def _cluster_summary(
    cell_id: str,
    cluster_id: str,
    token_summary: Mapping[str, str],
    interpretation_status: str,
) -> str:
    if interpretation_status != "interpreted":
        return f"normal cluster {cluster_id} in cell {cell_id}; token bins unavailable"
    parts: list[str] = []
    motion = token_summary.get("motion")
    density = token_summary.get("density")
    brightness = token_summary.get("brightness")
    direction = token_summary.get("direction")
    if motion:
        parts.append(f"{motion} motion")
    if density:
        parts.append(f"{density} density")
    if brightness:
        parts.append(f"{brightness} brightness")
    if direction:
        parts.append(f"{direction} direction")
    if not parts:
        return f"normal cluster {cluster_id} in cell {cell_id}"
    return f"normal {'; '.join(parts)} in cell {cell_id}"


def _iter_cluster_rows(payload: Mapping[str, Any]):
    for cell in payload.get("cells", []):
        for cluster in cell.get("clusters", []):
            yield {
                "cell_id": str(cell.get("cell_id", "")),
                "cluster_id": str(cluster.get("cluster_id", "")),
                "support": _float_or_none(cluster.get("support")),
                "threshold": _float_or_none(cell.get("threshold")),
                "token_map": dict(cluster.get("token_summary", {})),
                "summary": str(cluster.get("summary", "")),
            }


def _token_map(tokens: list[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if key in SUMMARY_TOKEN_PREFIXES:
            mapped[key] = value
    return mapped


def _parse_cell_id(cell_id: str) -> tuple[int, int] | None:
    try:
        row, col = cell_id.split("_", 1)
        return int(row), int(col)
    except (ValueError, TypeError):
        return None


def _float_or_none(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(value):
        return None
    return value


def _int_or_none(raw: Any) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _clip_probability(value: float) -> float:
    return float(np.clip(float(value), 0.0, 1.0))


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
