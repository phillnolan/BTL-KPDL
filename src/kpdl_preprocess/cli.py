from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import run_preprocess


SRC_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run preprocessing for the anomaly detection pipeline.")
    parser.add_argument("--config", required=True, help="Path to a YAML config file.")
    parser.add_argument(
        "--project-root",
        default=str(SRC_ROOT),
        help="Runtime root for resolving dataset/output paths. Defaults to the src directory.",
    )
    parser.add_argument("--output-root", default=None, help="Override output root, for example outputs/preprocessed_smoke.")
    parser.add_argument("--split", choices=["train", "test"], default=None, help="Process only one split.")
    parser.add_argument("--limit-videos", type=int, default=None, help="Limit videos/sequences per split for smoke tests.")
    parser.add_argument("--limit-frames", type=int, default=None, help="Limit frames per video/sequence for smoke tests.")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=250,
        help="Print progress every N frames while processing videos/sequences. Use 0 to disable.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stats = run_preprocess(
        config_path=args.config,
        project_root=Path(args.project_root),
        output_root=args.output_root,
        split=args.split,
        limit_videos=args.limit_videos,
        limit_frames=args.limit_frames,
        progress_every=args.progress_every,
    )
    print(json.dumps(_public_stats(stats), indent=2))
    return 0


def _public_stats(stats: dict) -> dict:
    return {
        "dataset": stats.get("dataset"),
        "output_dir": stats.get("output_dir"),
        "splits": stats.get("splits"),
    }
