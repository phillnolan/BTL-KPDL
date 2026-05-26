from __future__ import annotations

import argparse
import json
from pathlib import Path

from kpdl_preprocess.config import resolve_path

from .config import load_anomaly_config
from .scoring import score_features


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score SPEC 3 anomaly models on test features.")
    parser.add_argument("--config", required=True, help="Path to a YAML config file.")
    parser.add_argument("--project-root", default=".", help="Project root. Relative paths are resolved here.")
    parser.add_argument("--model", default=None, help="Model directory. Defaults to output.model_root/dataset.")
    parser.add_argument("--result-root", default=None, help="Override result root.")
    parser.add_argument("--limit-rows", type=int, default=None, help="Limit test feature rows for smoke tests.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_test(
        config_path=args.config,
        project_root=args.project_root,
        model_dir=args.model,
        result_root=args.result_root,
        limit_rows=args.limit_rows,
    )
    print(json.dumps(_public_summary(summary), indent=2))
    return 0


def run_test(
    config_path: str | Path,
    project_root: str | Path = ".",
    model_dir: str | Path | None = None,
    result_root: str | Path | None = None,
    limit_rows: int | None = None,
) -> dict:
    config = load_anomaly_config(
        config_path=config_path,
        project_root=project_root,
        result_root=result_root,
    )
    resolved_model_dir = resolve_path(model_dir, config.project_root) if model_dir is not None else config.model_dir
    return score_features(config, model_dir=resolved_model_dir, result_dir=config.result_dir, limit_rows=limit_rows)


def _public_summary(summary: dict) -> dict:
    return {
        "dataset": summary["dataset"],
        "result_dir": summary["result_dir"],
        "rows_scored": summary["rows_scored"],
        "num_frames": summary["num_frames"],
        "severity_counts": summary["severity_counts"],
        "num_alerts": summary["num_alerts"],
    }
