from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kpdl_anomaly.config import load_anomaly_config
from kpdl_anomaly.rule_model import train_rule_model
from kpdl_preprocess.config import resolve_path


SRC_ROOT = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train SPEC 5 token/rule artifacts.")
    parser.add_argument("--config", required=True, help="Path to a YAML config file.")
    parser.add_argument(
        "--project-root",
        default=str(SRC_ROOT),
        help="Runtime root for resolving dataset/output paths. Defaults to the src directory.",
    )
    parser.add_argument("--model", default=None, help="SPEC 3 model directory. Defaults to output.model_root/dataset.")
    parser.add_argument("--output-dir", default=None, help="Override rule artifact directory.")
    parser.add_argument("--limit-rows", type=int, default=None, help="Limit train feature rows for smoke tests.")
    parser.add_argument("--write-transactions", action="store_true", help="Write all train transactions as JSONL.")
    parser.add_argument("--min-support", type=float, default=None, help="Override rules.min_support.")
    parser.add_argument("--min-confidence", type=float, default=None, help="Override rules.min_confidence.")
    parser.add_argument("--min-lift", type=float, default=None, help="Override rules.min_lift.")
    parser.add_argument("--max-rules", type=int, default=None, help="Override rules.max_rules.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_rules(
        config_path=args.config,
        project_root=args.project_root,
        model_dir=args.model,
        output_dir=args.output_dir,
        limit_rows=args.limit_rows,
        write_transactions=args.write_transactions,
        min_support=args.min_support,
        min_confidence=args.min_confidence,
        min_lift=args.min_lift,
        max_rules=args.max_rules,
    )
    print(json.dumps(_public_summary(summary), indent=2))
    return 0


def run_rules(
    config_path: str | Path,
    project_root: str | Path = SRC_ROOT,
    model_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    limit_rows: int | None = None,
    write_transactions: bool = False,
    min_support: float | None = None,
    min_confidence: float | None = None,
    min_lift: float | None = None,
    max_rules: int | None = None,
) -> dict:
    config = load_anomaly_config(config_path=config_path, project_root=project_root)
    config = _with_overrides(
        config,
        min_support=min_support,
        min_confidence=min_confidence,
        min_lift=min_lift,
        max_rules=max_rules,
    )
    resolved_model_dir = resolve_path(model_dir, config.project_root) if model_dir is not None else config.model_dir
    resolved_output_dir = resolve_path(output_dir, config.project_root) if output_dir is not None else None
    return train_rule_model(
        config,
        model_dir=resolved_model_dir,
        output_path=resolved_output_dir,
        limit_rows=limit_rows,
        write_transactions=write_transactions,
    )


def _with_overrides(
    config,
    min_support: float | None,
    min_confidence: float | None,
    min_lift: float | None,
    max_rules: int | None,
):
    rules = config.rules
    if min_support is not None:
        rules = replace(rules, min_support=min_support)
    if min_confidence is not None:
        rules = replace(rules, min_confidence=min_confidence)
    if min_lift is not None:
        rules = replace(rules, min_lift=min_lift)
    if max_rules is not None:
        rules = replace(rules, max_rules=max_rules)
    return replace(config, rules=rules)


def _public_summary(summary: dict) -> dict:
    manifest = summary["manifest"]
    return {
        "dataset": summary["dataset"],
        "rule_dir": summary["rule_dir"],
        "num_transactions": manifest["num_transactions"],
        "num_itemsets": manifest["num_itemsets"],
        "num_rules": manifest["num_rules"],
        "warnings": manifest["warnings"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
