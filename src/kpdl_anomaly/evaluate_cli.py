from __future__ import annotations

import argparse
import json
from pathlib import Path

from kpdl_preprocess.config import resolve_path

from .config import load_anomaly_config
from .evaluation import evaluate_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate frame-level anomaly metrics for one pipeline result.")
    parser.add_argument("--config", required=True, help="Path to a YAML config file.")
    parser.add_argument("--project-root", default=".", help="Project root. Relative paths are resolved here.")
    parser.add_argument("--results", default=None, help="Single result directory to evaluate.")
    parser.add_argument("--output-dir", default=None, help="Directory for evaluation artifacts.")
    parser.add_argument(
        "--score-columns",
        nargs="+",
        default=None,
        help="Frame score columns to evaluate. Defaults to evaluation.score_columns.",
    )
    parser.add_argument(
        "--label-source",
        choices=["auto", "mask", "interval"],
        default=None,
        help="Ground-truth source. Defaults to evaluation.label_source.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_anomaly_config(config_path=args.config, project_root=args.project_root)
    output_dir = resolve_path(args.output_dir, config.project_root) if args.output_dir else None
    result_dir = resolve_path(args.results, config.project_root) if args.results else config.result_dir
    summary = evaluate_results(
        config,
        result_dir=result_dir,
        output_dir=output_dir,
        score_columns=args.score_columns,
        label_source=args.label_source,
    )

    print(json.dumps(_public_summary(summary), indent=2, ensure_ascii=False))
    return 0


def _public_summary(summary: dict) -> dict:
    return {
        "dataset": summary["dataset"],
        "output_dir": summary["output_dir"],
        "frames": summary["frames"],
        "metrics": summary["metrics"],
    }
