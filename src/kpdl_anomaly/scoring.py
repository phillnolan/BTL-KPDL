from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from kpdl_preprocess.config import ConfigError

from .alerts import assign_severities, build_alerts
from .config import AnomalyConfig
from .feature_selection import row_to_vector
from .io import output_dir, read_json, require_files, validate_feature_header, write_json
from .rule_scoring import RuleScore, load_rule_scorer
from .schema import CELL_SCORE_COLUMNS, FRAME_SCORE_COLUMNS, METADATA_COLUMNS, RULE_SCORE_COLUMNS, SCHEMA_VERSION
from .smoothing import moving_average
from .thresholds import distance_to_score


def score_features(
    config: AnomalyConfig,
    model_dir: str | Path,
    result_dir: str | Path | None = None,
    limit_rows: int | None = None,
    rules_dir: str | Path | None = None,
    use_rules: bool | None = None,
) -> dict[str, Any]:
    model_dir = Path(model_dir)
    result_path = output_dir(result_dir or config.result_dir)
    require_files(
        [
            config.test_feature_path,
            model_dir / "model_manifest.json",
            model_dir / "cell_models.joblib",
            model_dir / "cell_scalers.joblib",
            model_dir / "thresholds.json",
        ]
    )
    required_columns = METADATA_COLUMNS + config.feature_columns
    validate_feature_header(config.test_feature_path, required_columns)

    manifest = read_json(model_dir / "model_manifest.json")
    _validate_manifest(config, manifest)
    models = joblib.load(model_dir / "cell_models.joblib")
    scalers = joblib.load(model_dir / "cell_scalers.joblib")
    thresholds_payload = read_json(model_dir / "thresholds.json")
    thresholds = dict(thresholds_payload.get("cells", {}))
    requested_rules = config.rules.enabled if use_rules is None else bool(use_rules)
    rule_load = load_rule_scorer(config, rules_dir, requested=requested_rules)
    rule_scorer = rule_load.scorer
    rules_active = rule_scorer is not None
    score_weights = _score_weights(config, rules_active)

    cell_scores_path = result_path / "cell_scores.csv"
    cell_score_columns = CELL_SCORE_COLUMNS + (RULE_SCORE_COLUMNS if rules_active else [])
    frame_groups: dict[tuple[str, str, str, int], list[dict[str, Any]]] = {}
    previous_cluster_scores: dict[tuple[str, str], float] = {}
    rare_scores: list[float] = []
    rule_violation_scores: list[float] = []
    token_reason_rows = 0
    rows_read = 0
    rows_scored = 0
    invalid_rows = 0
    split_mismatches = 0
    fallback_rows = 0

    with config.test_feature_path.open("r", newline="", encoding="utf-8") as input_handle, cell_scores_path.open(
        "w", newline="", encoding="utf-8"
    ) as output_handle:
        reader = csv.DictReader(input_handle)
        writer = csv.DictWriter(output_handle, fieldnames=cell_score_columns)
        writer.writeheader()

        for row in reader:
            if limit_rows is not None and rows_read >= limit_rows:
                break
            rows_read += 1
            if row.get("split") != "test":
                split_mismatches += 1
                continue
            vector = row_to_vector(row, config.feature_columns)
            if vector is None:
                invalid_rows += 1
                continue

            cell_id = str(row["cell_id"])
            score = _score_row(cell_id, vector, models, scalers, thresholds)
            if not score["trained"]:
                fallback_rows += 1

            temporal_key = (str(row["video_id"]), cell_id)
            previous = previous_cluster_scores.get(temporal_key)
            temporal_change_score = 0.0 if previous is None else abs(score["cluster_distance_score"] - previous)
            temporal_change_score = float(np.clip(temporal_change_score, 0.0, 1.0))
            previous_cluster_scores[temporal_key] = score["cluster_distance_score"]

            rule_score = _empty_rule_score()
            if rule_scorer is not None:
                rule_score = rule_scorer.score(row, score["nearest_cluster"])
                rare_scores.append(rule_score.rare_token_score)
                rule_violation_scores.append(rule_score.rule_violation_score)
                if rule_score.reasons:
                    token_reason_rows += 1

            cell_score = (
                score_weights["cluster"] * score["cluster_distance_score"]
                + score_weights["temporal"] * temporal_change_score
                + score_weights["rare"] * rule_score.rare_token_score
                + score_weights["rule"] * rule_score.rule_violation_score
            )
            cell_score = float(np.clip(cell_score, 0.0, 1.0))

            output_row = {
                "dataset": row["dataset"],
                "split": row["split"],
                "video_id": row["video_id"],
                "cube_id": row["cube_id"],
                "start_frame_id": row["start_frame_id"],
                "end_frame_id": row["end_frame_id"],
                "center_frame_id": row["center_frame_id"],
                "cell_id": cell_id,
                "cell_row": row["cell_row"],
                "cell_col": row["cell_col"],
                "nearest_cluster": score["nearest_cluster"],
                "cluster_distance": _fmt(score["cluster_distance"]),
                "cluster_threshold": _fmt(score["cluster_threshold"]),
                "cluster_distance_score": _fmt(score["cluster_distance_score"]),
                "temporal_change_score": _fmt(temporal_change_score),
                "cell_score": _fmt(cell_score),
            }
            if rules_active:
                output_row.update(_rule_output_columns(rule_score))
            writer.writerow(output_row)

            frame_id = int(row["center_frame_id"])
            frame_key = (str(row["dataset"]), str(row["split"]), str(row["video_id"]), frame_id)
            _add_top_cell(
                frame_groups,
                frame_key,
                {
                    "cell_id": cell_id,
                    "cell_score": cell_score,
                    "cluster_distance": score["cluster_distance"],
                    "cluster_threshold": score["cluster_threshold"],
                    "nearest_cluster": score["nearest_cluster"],
                    "rare_token_score": rule_score.rare_token_score,
                    "rule_violation_score": rule_score.rule_violation_score,
                    "token_rule_reasons": rule_score.reasons,
                },
                config.top_k_cells,
            )
            rows_scored += 1

    if split_mismatches:
        raise ConfigError(f"{config.test_feature_path} contains {split_mismatches} row(s) outside split='test'")

    frame_records = _frame_records(frame_groups)
    records_by_video = _smooth_and_label(config, frame_records)
    alerts = build_alerts(config.dataset, records_by_video, config.min_consecutive_alerts)

    frame_scores_path = result_path / "frame_scores.csv"
    with frame_scores_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FRAME_SCORE_COLUMNS)
        writer.writeheader()
        for record in frame_records:
            writer.writerow(
                {
                    "dataset": record["dataset"],
                    "split": record["split"],
                    "video_id": record["video_id"],
                    "frame_id": record["frame_id"],
                    "frame_score": _fmt(record["frame_score"]),
                    "smoothed_frame_score": _fmt(record["smoothed_frame_score"]),
                    "severity": record["severity"],
                    "top_cells": json.dumps(record["top_cells"], ensure_ascii=False),
                }
            )

    stats = _stats(
        config=config,
        model_dir=model_dir,
        result_path=result_path,
        rows_read=rows_read,
        rows_scored=rows_scored,
        invalid_rows=invalid_rows,
        fallback_rows=fallback_rows,
        frame_records=frame_records,
        alerts=alerts,
        limit_rows=limit_rows,
        rule_dir=rule_load.rule_dir,
        rule_warnings=rule_load.warnings,
        rules_requested=requested_rules,
        rules_active=rules_active,
        score_weights=score_weights,
        rare_scores=rare_scores,
        rule_violation_scores=rule_violation_scores,
        token_reason_rows=token_reason_rows,
    )
    write_json(result_path / "alerts.json", alerts)
    write_json(result_path / "scoring_stats.json", stats)
    return stats


def _validate_manifest(config: AnomalyConfig, manifest: dict[str, Any]) -> None:
    if manifest.get("dataset") != config.dataset:
        raise ConfigError(f"model dataset={manifest.get('dataset')!r} does not match config dataset={config.dataset!r}")
    if list(manifest.get("feature_columns", [])) != config.feature_columns:
        raise ConfigError("model feature_columns do not match config scoring.feature_columns")


def _score_weights(config: AnomalyConfig, rules_active: bool) -> dict[str, float]:
    if rules_active:
        return {
            "cluster": config.cluster_weight,
            "temporal": config.temporal_weight,
            "rare": config.rare_token_weight,
            "rule": config.rule_weight,
        }
    if config.rare_token_weight > 0.0 or config.rule_weight > 0.0:
        return {"cluster": 0.80, "temporal": 0.20, "rare": 0.0, "rule": 0.0}
    return {"cluster": config.cluster_weight, "temporal": config.temporal_weight, "rare": 0.0, "rule": 0.0}


def _empty_rule_score() -> RuleScore:
    return RuleScore(
        tokens=[],
        rare_token_score=0.0,
        rare_itemset=[],
        rare_itemset_support=0.0,
        rule_violation_score=0.0,
        violated_rules=[],
        reasons=[],
    )


def _rule_output_columns(rule_score: RuleScore) -> dict[str, str]:
    return {
        "tokens": json.dumps(rule_score.tokens, ensure_ascii=False),
        "rare_token_score": _fmt(rule_score.rare_token_score),
        "rare_itemset": json.dumps(rule_score.rare_itemset, ensure_ascii=False),
        "rare_itemset_support": _fmt(rule_score.rare_itemset_support),
        "rule_violation_score": _fmt(rule_score.rule_violation_score),
        "violated_rules": json.dumps(rule_score.violated_rules, ensure_ascii=False),
        "token_rule_reasons": json.dumps(rule_score.reasons, ensure_ascii=False),
    }


def _score_row(
    cell_id: str,
    vector: np.ndarray,
    models: dict[str, Any],
    scalers: dict[str, Any],
    thresholds: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    model = models.get(cell_id)
    scaler = scalers.get(cell_id)
    threshold_info = thresholds.get(cell_id, {})
    threshold = float(threshold_info.get("threshold", 0.0))
    if model is None or scaler is None:
        return {
            "trained": False,
            "nearest_cluster": -1,
            "cluster_distance": 0.0,
            "cluster_threshold": threshold,
            "cluster_distance_score": 0.0,
        }

    scaled = scaler.transform(vector.reshape(1, -1))
    distances = model.transform(scaled)[0]
    nearest_cluster = int(np.argmin(distances))
    distance = float(distances[nearest_cluster])
    return {
        "trained": True,
        "nearest_cluster": nearest_cluster,
        "cluster_distance": distance,
        "cluster_threshold": threshold,
        "cluster_distance_score": distance_to_score(distance, threshold),
    }


def _add_top_cell(
    frame_groups: dict[tuple[str, str, str, int], list[dict[str, Any]]],
    frame_key: tuple[str, str, str, int],
    entry: dict[str, Any],
    top_k: int,
) -> None:
    top_entries = frame_groups.setdefault(frame_key, [])
    top_entries.append(entry)
    top_entries.sort(key=lambda item: float(item["cell_score"]), reverse=True)
    if len(top_entries) > top_k:
        top_entries.pop()


def _frame_records(frame_groups: dict[tuple[str, str, str, int], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for (dataset, split, video_id, frame_id), top_entries in sorted(frame_groups.items()):
        frame_score = float(np.mean([entry["cell_score"] for entry in top_entries])) if top_entries else 0.0
        records.append(
            {
                "dataset": dataset,
                "split": split,
                "video_id": video_id,
                "frame_id": frame_id,
                "frame_score": frame_score,
                "smoothed_frame_score": frame_score,
                "severity": "none",
                "top_entries": top_entries,
                "top_cells": [entry["cell_id"] for entry in top_entries],
            }
        )
    return records


def _smooth_and_label(
    config: AnomalyConfig,
    frame_records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    records_by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in frame_records:
        records_by_video[str(record["video_id"])].append(record)

    for records in records_by_video.values():
        records.sort(key=lambda item: int(item["frame_id"]))
        smoothed = moving_average([float(record["frame_score"]) for record in records], config.smoothing_window)
        for record, value in zip(records, smoothed, strict=True):
            record["smoothed_frame_score"] = float(np.clip(value, 0.0, 1.0))
        assign_severities(
            records,
            medium_threshold=config.alert_threshold_medium,
            high_threshold=config.alert_threshold_high,
            min_consecutive=config.min_consecutive_alerts,
        )
    frame_records.sort(key=lambda item: (str(item["video_id"]), int(item["frame_id"])))
    return dict(records_by_video)


def _stats(
    config: AnomalyConfig,
    model_dir: Path,
    result_path: Path,
    rows_read: int,
    rows_scored: int,
    invalid_rows: int,
    fallback_rows: int,
    frame_records: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    limit_rows: int | None,
    rule_dir: Path | None,
    rule_warnings: list[str],
    rules_requested: bool,
    rules_active: bool,
    score_weights: dict[str, float],
    rare_scores: list[float],
    rule_violation_scores: list[float],
    token_reason_rows: int,
) -> dict[str, Any]:
    frame_scores = [float(record["frame_score"]) for record in frame_records]
    smoothed_scores = [float(record["smoothed_frame_score"]) for record in frame_records]
    severity_counts = {
        "none": sum(1 for record in frame_records if record["severity"] == "none"),
        "medium": sum(1 for record in frame_records if record["severity"] == "medium"),
        "high": sum(1 for record in frame_records if record["severity"] == "high"),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset": config.dataset,
        "split": "test",
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "test_feature_path": str(config.test_feature_path),
        "model_dir": str(model_dir),
        "result_dir": str(result_path),
        "rows_read": rows_read,
        "rows_scored": rows_scored,
        "invalid_rows": invalid_rows,
        "fallback_rows": fallback_rows,
        "limit_rows": limit_rows,
        "num_frames": len(frame_records),
        "severity_counts": severity_counts,
        "num_alerts": len(alerts),
        "frame_score": _distribution(frame_scores),
        "smoothed_frame_score": _distribution(smoothed_scores),
        "rules": {
            "requested": rules_requested,
            "active": rules_active,
            "rule_dir": str(rule_dir) if rule_dir is not None else None,
            "warnings": rule_warnings,
            "score_weights": score_weights,
            "token_reason_rows": token_reason_rows,
            "rare_token_score": _distribution(rare_scores),
            "rule_violation_score": _distribution(rule_violation_scores),
        },
    }


def _distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "mean": 0.0, "max": 0.0}
    arr = np.asarray(values, dtype=np.float64)
    return {"min": float(np.min(arr)), "mean": float(np.mean(arr)), "max": float(np.max(arr))}


def _fmt(value: float) -> str:
    return f"{float(value):.8f}"
