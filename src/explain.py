from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kpdl_preprocess.config import resolve_path
from kpdl_preprocess.utils import ensure_dir

from kpdl_anomaly.casebook import generate_casebook
from kpdl_anomaly.cluster_profiles import ANALYSIS_SCHEMA_VERSION, generate_cluster_profiles
from kpdl_anomaly.config import load_anomaly_config
from kpdl_anomaly.explanations import RuleEvidenceResult, write_rule_evidence_index
from kpdl_anomaly.io import write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build SPEC 9 cluster profiles and alert casebook artifacts.")
    parser.add_argument("--config", required=True, help="Path to a YAML config file.")
    parser.add_argument("--project-root", default=".", help="Project root. Relative paths are resolved here.")
    parser.add_argument("--model", default=None, help="Model artifact directory. Defaults to output.model_root/dataset.")
    parser.add_argument("--rules", default=None, help="Rule artifact directory. Defaults to rules.output_root/dataset.")
    parser.add_argument("--results", default=None, help="Result artifact directory. Defaults to output.result_root/dataset.")
    parser.add_argument(
        "--visualizations",
        default=None,
        help="Visualization artifact directory. Defaults to visualization.output_root/dataset.",
    )
    parser.add_argument("--output-dir", required=True, help="Directory for SPEC 9 analysis artifacts.")
    parser.add_argument("--top-alerts", type=int, default=None, help="Maximum alert peak cases to include.")
    parser.add_argument(
        "--top-frames",
        type=int,
        default=None,
        help="Optional number of top frame-score cases to include.",
    )
    parser.add_argument("--video-id", default=None, help="Restrict case selection to one video.")
    parser.add_argument("--start-frame", type=int, default=None, help="Restrict case selection to frames >= this value.")
    parser.add_argument("--end-frame", type=int, default=None, help="Restrict case selection to frames <= this value.")
    parser.add_argument("--no-rules", action="store_true", help="Skip rule artifacts and rule evidence.")
    parser.add_argument(
        "--write-cluster-profiles-only",
        action="store_true",
        help="Write only cluster_profiles.json/md and a lightweight manifest.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_explain(
        config_path=args.config,
        project_root=args.project_root,
        model_dir=args.model,
        rules_dir=args.rules,
        result_dir=args.results,
        visualizations_dir=args.visualizations,
        output_dir=args.output_dir,
        top_alerts=args.top_alerts,
        top_frames=args.top_frames,
        video_id=args.video_id,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        no_rules=args.no_rules,
        write_cluster_profiles_only=args.write_cluster_profiles_only,
    )
    print(json.dumps(_public_summary(summary), indent=2))
    return 0


def run_explain(
    config_path: str | Path,
    project_root: str | Path = ".",
    model_dir: str | Path | None = None,
    rules_dir: str | Path | None = None,
    result_dir: str | Path | None = None,
    visualizations_dir: str | Path | None = None,
    output_dir: str | Path = "src/outputs/analysis/default",
    top_alerts: int | None = None,
    top_frames: int | None = None,
    video_id: str | None = None,
    start_frame: int | None = None,
    end_frame: int | None = None,
    no_rules: bool = False,
    write_cluster_profiles_only: bool = False,
) -> dict[str, Any]:
    config = load_anomaly_config(config_path=config_path, project_root=project_root)
    output_path = ensure_dir(resolve_path(output_dir, config.project_root))
    model_path = resolve_path(model_dir, config.project_root) if model_dir is not None else config.model_dir
    requested_rules = not no_rules
    rule_path = (
        None
        if no_rules
        else (resolve_path(rules_dir, config.project_root) if rules_dir is not None else config.rules.output_root / config.dataset)
    )
    result_path = resolve_path(result_dir, config.project_root) if result_dir is not None else config.result_dir
    visualization_path = (
        resolve_path(visualizations_dir, config.project_root)
        if visualizations_dir is not None
        else _default_visualization_dir(config)
    )

    cluster_profiles = generate_cluster_profiles(
        config=config,
        model_dir=model_path,
        output_dir=output_path,
        rules_dir=rule_path,
        use_rules=requested_rules,
    )

    if write_cluster_profiles_only:
        rule_evidence = RuleEvidenceResult(
            records=[],
            evidence_by_id={},
            min_support=config.rules.min_support,
            rule_dir=rule_path,
            requested=requested_rules,
            active=False,
            warnings=[] if requested_rules else ["rule evidence skipped because rules were disabled for this run"],
        )
        manifest = _cluster_only_manifest(config, output_path, model_path, rule_evidence, cluster_profiles)
        write_json(output_path / "analysis_manifest.json", manifest)
        return {
            "dataset": config.dataset,
            "output_dir": str(output_path),
            "cluster_profiles": cluster_profiles,
            "rule_evidence": rule_evidence,
            "casebook": None,
            "manifest": manifest,
        }

    rule_evidence = write_rule_evidence_index(
        config=config,
        output_dir=output_path,
        rules_dir=rule_path,
        requested=requested_rules,
    )
    effective_top_alerts = 20 if top_alerts is None and top_frames is None else top_alerts
    generated = generate_casebook(
        config=config,
        result_dir=result_path,
        output_dir=output_path,
        cluster_profiles=cluster_profiles,
        rule_evidence=rule_evidence,
        model_dir=model_path,
        visualizations_dir=visualization_path,
        top_alerts=effective_top_alerts,
        top_frames=top_frames,
        video_id=video_id,
        start_frame=start_frame,
        end_frame=end_frame,
    )
    return {
        "dataset": config.dataset,
        "output_dir": str(output_path),
        "cluster_profiles": cluster_profiles,
        "rule_evidence": rule_evidence,
        "casebook": generated["casebook"],
        "manifest": generated["manifest"],
    }


def _default_visualization_dir(config: Any) -> Path:
    raw = config.raw.setdefault("visualization", {})
    output_root = str(raw.setdefault("output_root", "src/outputs/visualizations"))
    return resolve_path(output_root, config.project_root) / config.dataset


def _cluster_only_manifest(
    config: Any,
    output_path: Path,
    model_dir: str | Path,
    rule_evidence: RuleEvidenceResult,
    cluster_profiles: dict[str, Any],
) -> dict[str, Any]:
    warnings = list(cluster_profiles.get("warnings", [])) + list(rule_evidence.warnings)
    return {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "dataset": config.dataset,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config.config_path),
        "inputs": {
            "model_dir": str(model_dir),
            "rule_dir": str(rule_evidence.rule_dir) if rule_evidence.rule_dir is not None else None,
            "result_dir": None,
            "visualizations_dir": None,
        },
        "outputs": {
            "cluster_profiles_json": str(output_path / "cluster_profiles.json"),
            "cluster_profiles_md": str(output_path / "cluster_profiles.md"),
            "analysis_manifest_json": str(output_path / "analysis_manifest.json"),
        },
        "counts": {
            "cluster_profile_cells": int(cluster_profiles.get("num_cells", 0)),
            "cluster_profiles": int(cluster_profiles.get("num_clusters", 0)),
            "rule_evidence": 0,
            "cases": 0,
        },
        "warnings": warnings,
    }


def _public_summary(summary: dict[str, Any]) -> dict[str, Any]:
    rule_evidence: RuleEvidenceResult = summary["rule_evidence"]
    casebook = summary.get("casebook") or {}
    cluster_profiles = summary["cluster_profiles"]
    return {
        "dataset": summary["dataset"],
        "output_dir": summary["output_dir"],
        "cluster_profiles": {
            "cells": cluster_profiles.get("num_cells", 0),
            "clusters": cluster_profiles.get("num_clusters", 0),
            "warnings": len(cluster_profiles.get("warnings", [])),
        },
        "rule_evidence": {
            "requested": rule_evidence.requested,
            "active": rule_evidence.active,
            "rules": len(rule_evidence.records),
            "warnings": len(rule_evidence.warnings),
        },
        "casebook": {
            "cases": len(casebook.get("cases", [])),
            "warnings": len(casebook.get("warnings", [])),
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
