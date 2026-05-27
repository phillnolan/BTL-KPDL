from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from kpdl_preprocess.config import ConfigError

from .association import generate_association_rules, itemset_records, update_itemset_counts
from .config import AnomalyConfig
from .feature_selection import row_to_vector
from .io import output_dir, read_json, require_files, validate_feature_header, write_json
from .schema import METADATA_COLUMNS, RULE_SCHEMA_VERSION
from .tokenization import fit_token_bins, row_to_tokens

SAMPLE_TRANSACTION_LIMIT = 200


def train_rule_model(
    config: AnomalyConfig,
    model_dir: str | Path,
    output_path: str | Path | None = None,
    limit_rows: int | None = None,
    write_transactions: bool = False,
) -> dict[str, Any]:
    model_path = Path(model_dir)
    rule_path = output_dir(output_path or (config.rules.output_root / config.dataset))
    require_files(
        [
            config.train_feature_path,
            model_path / "model_manifest.json",
            model_path / "cell_models.joblib",
            model_path / "cell_scalers.joblib",
            model_path / "thresholds.json",
        ]
    )
    validate_feature_header(config.train_feature_path, METADATA_COLUMNS + config.feature_columns)

    model_manifest = read_json(model_path / "model_manifest.json")
    _validate_model_manifest(config, model_manifest)
    models = joblib.load(model_path / "cell_models.joblib")
    scalers = joblib.load(model_path / "cell_scalers.joblib")

    token_bins = fit_token_bins(config.train_feature_path, expected_split="train", limit_rows=limit_rows)
    itemset_counter: Counter[tuple[str, ...]] = Counter()
    token_counter: Counter[str] = Counter()
    rows_read = 0
    rows_loaded = 0
    invalid_rows = 0
    split_mismatches = 0
    fallback_cluster_rows = 0
    empty_token_rows = 0

    sample_path = rule_path / "train_tokens_sample.jsonl"
    transaction_path = rule_path / "train_transactions.jsonl"
    with config.train_feature_path.open("r", newline="", encoding="utf-8") as input_handle, sample_path.open(
        "w", encoding="utf-8"
    ) as sample_handle:
        transaction_handle = transaction_path.open("w", encoding="utf-8") if write_transactions else None
        try:
            reader = csv.DictReader(input_handle)
            for row in reader:
                if limit_rows is not None and rows_read >= limit_rows:
                    break
                rows_read += 1
                if row.get("split") != "train":
                    split_mismatches += 1
                    continue

                vector = row_to_vector(row, config.feature_columns)
                if vector is None:
                    invalid_rows += 1
                    continue

                cluster_id = _nearest_cluster(str(row["cell_id"]), vector, models, scalers)
                if cluster_id < 0:
                    fallback_cluster_rows += 1

                tokens = row_to_tokens(
                    row,
                    token_bins,
                    cluster_id,
                    include_cell_token=config.rules.include_cell_token,
                    include_cluster_token=config.rules.include_cluster_token,
                    include_brightness_token=config.rules.include_brightness_token,
                    include_direction_token=config.rules.include_direction_token,
                )
                if not tokens:
                    empty_token_rows += 1
                    continue

                rows_loaded += 1
                token_counter.update(tokens)
                update_itemset_counts(itemset_counter, tokens, config.rules.max_itemset_size)

                record = _transaction_record(row, tokens)
                if rows_loaded <= SAMPLE_TRANSACTION_LIMIT:
                    sample_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                if transaction_handle is not None:
                    transaction_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        finally:
            if transaction_handle is not None:
                transaction_handle.close()

    if split_mismatches:
        raise ConfigError(f"{config.train_feature_path} contains {split_mismatches} row(s) outside split='train'")
    if rows_loaded == 0:
        raise ConfigError("No valid train transactions were generated")

    itemsets = itemset_records(
        itemset_counter,
        rows_loaded,
        min_support=config.rules.rare_support_floor,
    )
    rules = generate_association_rules(
        itemset_counter,
        rows_loaded,
        min_support=config.rules.min_support,
        min_confidence=config.rules.min_confidence,
        min_lift=config.rules.min_lift,
        max_rules=config.rules.max_rules,
    )
    token_stats = _token_stats(token_counter, rows_loaded)
    warnings = _warnings(
        limit_rows=limit_rows,
        invalid_rows=invalid_rows,
        fallback_cluster_rows=fallback_cluster_rows,
        empty_token_rows=empty_token_rows,
        num_rules=len(rules),
    )
    created_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema_version": RULE_SCHEMA_VERSION,
        "dataset": config.dataset,
        "created_at": created_at,
        "config_path": str(config.config_path),
        "source_model_dir": str(model_path),
        "train_feature_path": str(config.train_feature_path),
        "feature_columns": config.feature_columns,
        "token_schema": _token_schema(config),
        "num_transactions": rows_loaded,
        "rows_read": rows_read,
        "invalid_rows": invalid_rows,
        "fallback_cluster_rows": fallback_cluster_rows,
        "num_itemsets": len(itemsets),
        "num_rules": len(rules),
        "min_support": config.rules.min_support,
        "min_confidence": config.rules.min_confidence,
        "min_lift": config.rules.min_lift,
        "max_itemset_size": config.rules.max_itemset_size,
        "rare_support_floor": config.rules.rare_support_floor,
        "limit_rows": limit_rows,
        "warnings": warnings,
    }

    write_json(rule_path / "rule_manifest.json", manifest)
    write_json(rule_path / "token_bins.json", token_bins)
    write_json(rule_path / "itemsets.json", itemsets)
    write_json(rule_path / "rules.json", rules)
    write_json(rule_path / "token_stats.json", token_stats)
    _write_selected_rules(rule_path / "selected_rules.md", rules, manifest)

    return {
        "dataset": config.dataset,
        "rule_dir": str(rule_path),
        "manifest": manifest,
        "token_bins_path": str(rule_path / "token_bins.json"),
        "itemsets_path": str(rule_path / "itemsets.json"),
        "rules_path": str(rule_path / "rules.json"),
        "selected_rules_path": str(rule_path / "selected_rules.md"),
    }


def _validate_model_manifest(config: AnomalyConfig, manifest: dict[str, Any]) -> None:
    if manifest.get("dataset") != config.dataset:
        raise ConfigError(f"model dataset={manifest.get('dataset')!r} does not match config dataset={config.dataset!r}")
    if list(manifest.get("feature_columns", [])) != config.feature_columns:
        raise ConfigError("model feature_columns do not match config scoring.feature_columns")


def _nearest_cluster(cell_id: str, vector: np.ndarray, models: dict[str, Any], scalers: dict[str, Any]) -> int:
    model = models.get(cell_id)
    scaler = scalers.get(cell_id)
    if model is None or scaler is None:
        return -1
    scaled = scaler.transform(vector.reshape(1, -1))
    distances = model.transform(scaled)[0]
    return int(np.argmin(distances))


def _transaction_record(row: dict[str, str], tokens: list[str]) -> dict[str, Any]:
    return {
        "dataset": row["dataset"],
        "split": row["split"],
        "video_id": row["video_id"],
        "cube_id": row["cube_id"],
        "center_frame_id": int(row["center_frame_id"]),
        "cell_id": row["cell_id"],
        "tokens": tokens,
    }


def _token_schema(config: AnomalyConfig) -> dict[str, Any]:
    return {
        "tokens": [
            "cell",
            "cell_row",
            "cell_col",
            "motion",
            "density",
            "brightness",
            "brightness_delta",
            "cluster",
        ],
        "include_cell_token": config.rules.include_cell_token,
        "include_cluster_token": config.rules.include_cluster_token,
        "include_brightness_token": config.rules.include_brightness_token,
        "include_direction_token": config.rules.include_direction_token,
    }


def _token_stats(token_counter: Counter[str], num_transactions: int) -> dict[str, Any]:
    records = [
        {
            "token": token,
            "count": int(count),
            "support": float(count / num_transactions),
        }
        for token, count in token_counter.items()
    ]
    records.sort(key=lambda item: (-float(item["support"]), item["token"]))
    return {
        "num_transactions": num_transactions,
        "num_tokens": len(records),
        "tokens": records,
    }


def _warnings(
    limit_rows: int | None,
    invalid_rows: int,
    fallback_cluster_rows: int,
    empty_token_rows: int,
    num_rules: int,
) -> list[str]:
    warnings: list[str] = []
    if limit_rows is not None:
        warnings.append(f"limit_rows={limit_rows} was applied; artifact is for smoke/debug use")
    if invalid_rows:
        warnings.append(f"skipped {invalid_rows} row(s) with invalid numeric feature values")
    if fallback_cluster_rows:
        warnings.append(f"{fallback_cluster_rows} row(s) used cluster=unknown because no cell model/scaler was found")
    if empty_token_rows:
        warnings.append(f"skipped {empty_token_rows} row(s) that produced no tokens")
    if num_rules < 20:
        warnings.append(f"only {num_rules} rule(s) passed filters; selected_rules.md may be sparse")
    return warnings


def _write_selected_rules(path: Path, rules: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    lines = [
        "# Selected Association Rules",
        "",
        f"Dataset: `{manifest['dataset']}`",
        f"Transactions: `{manifest['num_transactions']}`",
        f"Filters: support >= `{manifest['min_support']}`, confidence >= `{manifest['min_confidence']}`, lift >= `{manifest['min_lift']}`",
        "",
    ]
    if not rules:
        lines.append("No association rules passed the configured filters.")
    for rule in rules[:20]:
        lines.append(
            "- `{rule_id}`: {{{antecedent}}} -> {{{consequent}}} "
            "support={support:.4f}, confidence={confidence:.4f}, lift={lift:.4f}".format(
                rule_id=rule["rule_id"],
                antecedent=", ".join(rule["antecedent"]),
                consequent=", ".join(rule["consequent"]),
                support=float(rule["support"]),
                confidence=float(rule["confidence"]),
                lift=float(rule["lift"]),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
