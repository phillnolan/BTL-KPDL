from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from .config import load_anomaly_config
from .io import load_features_by_cell, output_dir, read_json, require_files, write_config_yaml, write_json
from .modeling import train_per_cell
from .schema import SCHEMA_VERSION


SRC_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train SPEC 3 per-cell anomaly models.")
    parser.add_argument("--config", required=True, help="Path to a YAML config file.")
    parser.add_argument(
        "--project-root",
        default=str(SRC_ROOT),
        help="Runtime root for resolving dataset/output paths. Defaults to the src directory.",
    )
    parser.add_argument("--model-root", default=None, help="Override output model root.")
    parser.add_argument("--clusters-per-cell", type=int, default=None, help="Override model.clusters_per_cell.")
    parser.add_argument("--threshold-percentile", type=float, default=None, help="Override model threshold percentile.")
    parser.add_argument("--limit-rows", type=int, default=None, help="Limit train feature rows for smoke tests.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_train(
        config_path=args.config,
        project_root=args.project_root,
        model_root=args.model_root,
        clusters_per_cell=args.clusters_per_cell,
        threshold_percentile=args.threshold_percentile,
        limit_rows=args.limit_rows,
    )
    print(json.dumps(_public_summary(summary), indent=2))
    return 0


def run_train(
    config_path: str | Path,
    project_root: str | Path = SRC_ROOT,
    model_root: str | Path | None = None,
    clusters_per_cell: int | None = None,
    threshold_percentile: float | None = None,
    limit_rows: int | None = None,
) -> dict[str, Any]:
    config = load_anomaly_config(
        config_path=config_path,
        project_root=project_root,
        model_root=model_root,
        clusters_per_cell=clusters_per_cell,
        threshold_percentile=threshold_percentile,
    )
    require_files([config.train_feature_path, config.grid_path, config.preprocess_stats_path])

    grid = read_json(config.grid_path)
    preprocess_stats = read_json(config.preprocess_stats_path)
    cell_ids = [str(cell["cell_id"]) for cell in grid.get("cells", [])]
    loaded = load_features_by_cell(
        config.train_feature_path,
        feature_columns=config.feature_columns,
        expected_split="train",
        limit_rows=limit_rows,
    )
    training = train_per_cell(loaded.by_cell, cell_ids, config)

    model_dir = output_dir(config.model_dir)
    write_config_yaml(model_dir / "config.yaml", config.raw)
    joblib.dump(training.models, model_dir / "cell_models.joblib")
    joblib.dump(training.scalers, model_dir / "cell_scalers.joblib")

    expected_rows = _expected_rows(preprocess_stats, "train")
    warnings: list[str] = []
    if limit_rows is not None:
        warnings.append(f"limit_rows={limit_rows} was applied; artifact is for smoke/debug use")
    elif expected_rows is not None and expected_rows != loaded.rows_read:
        warnings.append(f"train row count mismatch: expected {expected_rows}, read {loaded.rows_read}")
    if loaded.invalid_rows:
        warnings.append(f"skipped {loaded.invalid_rows} row(s) with invalid numeric feature values")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset": config.dataset,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config.config_path),
        "feature_columns": config.feature_columns,
        "num_cells": int(grid.get("num_cells", len(cell_ids))),
        "num_models_trained": training.num_models_trained,
        "num_fallback_cells": training.num_fallback_cells,
        "clusters_per_cell": config.clusters_per_cell,
        "threshold_percentile": config.threshold_percentile,
        "threshold_floor": config.threshold_floor,
        "train_feature_path": str(config.train_feature_path),
        "grid_path": str(config.grid_path),
        "preprocess_schema_version": preprocess_stats.get("schema", {}).get("version"),
        "grid": {
            "rows": grid.get("rows"),
            "cols": grid.get("cols"),
            "num_cells": grid.get("num_cells"),
            "resized_width": grid.get("resized_width"),
            "resized_height": grid.get("resized_height"),
        },
        "train_rows_read": loaded.rows_read,
        "train_rows_loaded": loaded.rows_loaded,
        "invalid_rows": loaded.invalid_rows,
        "limit_rows": limit_rows,
        "warnings": warnings,
    }
    thresholds_payload = {
        "schema_version": SCHEMA_VERSION,
        "threshold_percentile": config.threshold_percentile,
        "cells": training.thresholds,
    }
    feature_stats_payload = dict(training.feature_stats)
    feature_stats_payload.update(
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": manifest["trained_at"],
            "train_rows_loaded": loaded.rows_loaded,
        }
    )

    write_json(model_dir / "model_manifest.json", manifest)
    write_json(model_dir / "thresholds.json", thresholds_payload)
    write_json(model_dir / "feature_stats.json", feature_stats_payload)

    return {
        "dataset": config.dataset,
        "model_dir": str(model_dir),
        "manifest": manifest,
        "thresholds_path": str(model_dir / "thresholds.json"),
        "feature_stats_path": str(model_dir / "feature_stats.json"),
    }


def _expected_rows(preprocess_stats: dict[str, Any], split: str) -> int | None:
    try:
        return int(preprocess_stats["splits"][split]["num_feature_rows"])
    except (KeyError, TypeError, ValueError):
        return None


def _public_summary(summary: dict[str, Any]) -> dict[str, Any]:
    manifest = summary["manifest"]
    return {
        "dataset": summary["dataset"],
        "model_dir": summary["model_dir"],
        "num_cells": manifest["num_cells"],
        "num_models_trained": manifest["num_models_trained"],
        "num_fallback_cells": manifest["num_fallback_cells"],
        "train_rows_read": manifest["train_rows_read"],
        "train_rows_loaded": manifest["train_rows_loaded"],
        "warnings": manifest["warnings"],
    }
