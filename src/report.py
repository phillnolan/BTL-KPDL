from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from kpdl_anomaly.reporting import ReportOptions, generate_report_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build SPEC 10 LaTeX report artifacts from analysis outputs.")
    parser.add_argument("--config", required=True, help="Path to a YAML config file.")
    parser.add_argument("--project-root", default=".", help="Project root. Relative paths are resolved here.")
    parser.add_argument("--analysis", required=True, help="SPEC 9 analysis artifact directory.")
    parser.add_argument("--results", default=None, help="Scoring result directory with frame/cell scores.")
    parser.add_argument("--visualizations", default=None, help="Visualization artifact directory.")
    parser.add_argument("--evaluation", default=None, help="Optional evaluation artifact directory.")
    parser.add_argument("--latex-dir", default="latex", help="LaTeX project directory.")
    parser.add_argument("--dataset", default=None, help="Dataset label for generated report folders.")
    parser.add_argument("--case-limit", type=int, default=5, help="Number of casebook cases to include.")
    parser.add_argument("--artifact-label", default="", help="Short label such as smoke or production.")
    parser.add_argument("--no-copy-figures", action="store_true", help="Reference source figures instead of copying them.")
    parser.add_argument("--sections-only", action="store_true", help="Write sections and tables without copying figures.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    options = ReportOptions(
        config_path=args.config,
        project_root=args.project_root,
        analysis_dir=args.analysis,
        results_dir=args.results,
        visualizations_dir=args.visualizations,
        evaluation_dir=args.evaluation,
        latex_dir=args.latex_dir,
        dataset=args.dataset,
        case_limit=args.case_limit,
        artifact_label=args.artifact_label,
        no_copy_figures=args.no_copy_figures,
        sections_only=args.sections_only,
    )
    manifest = generate_report_artifacts(options)
    print(json.dumps(_public_summary(manifest), indent=2))
    return 0


def _public_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    counts = dict(manifest.get("counts", {}))
    return {
        "dataset": manifest.get("dataset"),
        "artifact_label": manifest.get("artifact_label"),
        "manifest": manifest.get("outputs", {}).get("manifest"),
        "counts": {
            "cases": counts.get("cases", 0),
            "figures": counts.get("figures", 0),
            "cluster_profiles": counts.get("cluster_profiles", 0),
            "rule_evidence": counts.get("rule_evidence", 0),
        },
        "warnings": len(manifest.get("warnings", [])),
    }


if __name__ == "__main__":
    raise SystemExit(main())
