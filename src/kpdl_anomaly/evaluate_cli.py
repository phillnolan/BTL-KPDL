from __future__ import annotations

import argparse
import json
from pathlib import Path

from kpdl_preprocess.config import ConfigError, resolve_path

from .config import load_anomaly_config
from .evaluation import compare_result_sets, evaluate_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate SPEC 6 frame-level anomaly metrics.")
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
    parser.add_argument("--baseline-results", default=None, help="Baseline result directory for comparison.")
    parser.add_argument("--candidate-results", default=None, help="Candidate result directory for comparison.")
    parser.add_argument("--baseline-name", default="baseline", help="Baseline label in comparison output.")
    parser.add_argument("--candidate-name", default="candidate", help="Candidate label in comparison output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_anomaly_config(config_path=args.config, project_root=args.project_root)
    output_dir = resolve_path(args.output_dir, config.project_root) if args.output_dir else None

    if args.baseline_results or args.candidate_results:
        if not args.baseline_results or not args.candidate_results:
            raise ConfigError("--baseline-results and --candidate-results must be provided together")
        summary = compare_result_sets(
            config,
            baseline_result_dir=resolve_path(args.baseline_results, config.project_root),
            candidate_result_dir=resolve_path(args.candidate_results, config.project_root),
            output_dir=output_dir,
            score_columns=args.score_columns,
            label_source=args.label_source,
            baseline_name=args.baseline_name,
            candidate_name=args.candidate_name,
        )
    else:
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
    if "deltas" in summary:
        return {
            "dataset": summary["dataset"],
            "output_dir": summary["output_dir"],
            "baseline": summary["baseline"]["name"],
            "candidate": summary["candidate"]["name"],
            "deltas": summary["deltas"],
        }
    return {
        "dataset": summary["dataset"],
        "output_dir": summary["output_dir"],
        "frames": summary["frames"],
        "metrics": summary["metrics"],
    }
