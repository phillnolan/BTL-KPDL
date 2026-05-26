from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_ROOT.parent

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from kpdl_preprocess.pipeline import run_preprocess


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", default=str(PROJECT_ROOT), help="Project root for resolving dataset paths.")
    parser.add_argument("--output-root", default=None, help="Override output root, for example outputs/preprocessed.")
    parser.add_argument("--split", choices=["train", "test"], default=None, help="Process only one split.")
    parser.add_argument("--limit-videos", type=int, default=None, help="Limit videos/sequences per split for smoke tests.")
    parser.add_argument("--limit-frames", type=int, default=None, help="Limit frames per video/sequence for smoke tests.")
    parser.add_argument("--export-arff", action="store_true", help="Also export WEKA ARFF files from feature CSV outputs.")


def run_dataset(args: argparse.Namespace, config_path: Path) -> int:
    stats = run_preprocess(
        config_path=config_path,
        project_root=Path(args.project_root),
        output_root=args.output_root,
        split=args.split,
        limit_videos=args.limit_videos,
        limit_frames=args.limit_frames,
        export_arff=args.export_arff,
    )
    print(json.dumps(_summary(stats), indent=2, ensure_ascii=False))
    return 0


def _summary(stats: dict) -> dict:
    schema = stats.get("schema", {})
    return {
        "dataset": stats.get("dataset"),
        "output_dir": stats.get("output_dir"),
        "schema_version": schema.get("version"),
        "feature_columns": schema.get("feature_columns"),
        "splits": stats.get("splits"),
        "arff_outputs": stats.get("arff_outputs", []),
    }
