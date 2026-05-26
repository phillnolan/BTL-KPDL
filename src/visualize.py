from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kpdl_anomaly.visualization import run_visualization


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render SPEC 4 anomaly heatmap overlays.")
    parser.add_argument("--config", required=True, help="Path to a YAML config file.")
    parser.add_argument("--project-root", default=".", help="Project root. Relative paths are resolved here.")
    parser.add_argument("--result-dir", default=None, help="Override SPEC 3 result directory.")
    parser.add_argument("--output-dir", default=None, help="Override visualization output directory.")
    parser.add_argument("--top-frames", type=int, default=None, help="Export the top N anomaly frames.")
    parser.add_argument("--alerts", action="store_true", help="Export peak frames from alert segments.")
    parser.add_argument("--video-id", default=None, help="Video id to visualize.")
    parser.add_argument("--start-frame", type=int, default=None, help="First frame id for range/video export.")
    parser.add_argument("--end-frame", type=int, default=None, help="Last frame id for range/video export.")
    parser.add_argument("--write-video", action="store_true", help="Write an MP4 overlay for the selected video/range.")
    parser.add_argument("--alpha", type=float, default=None, help="Heatmap blend alpha override.")
    parser.add_argument("--colormap", default=None, help="OpenCV colormap name, for example JET or TURBO.")
    parser.add_argument("--min-score", type=float, default=None, help="Minimum smoothed score for top-frame export.")
    parser.add_argument("--limit-frames", type=int, default=None, help="Limit selected frames for quick smoke runs.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stats = run_visualization(
        config_path=args.config,
        project_root=args.project_root,
        result_dir=args.result_dir,
        output_dir=args.output_dir,
        top_frames=args.top_frames,
        include_alerts=args.alerts,
        video_id=args.video_id,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        write_video=args.write_video,
        alpha=args.alpha,
        colormap=args.colormap,
        min_score=args.min_score,
        limit_frames=args.limit_frames,
    )
    print(json.dumps(_public_summary(stats), indent=2))
    return 0


def _public_summary(stats: dict) -> dict:
    return {
        "dataset": stats["dataset"],
        "output_dir": stats["output_dir"],
        "num_frames_selected": stats["num_frames_selected"],
        "num_images_written": stats["num_images_written"],
        "num_videos_written": stats["num_videos_written"],
        "missing_frames": len(stats["missing_frames"]),
        "missing_cell_score_frames": len(stats["missing_cell_score_frames"]),
    }


if __name__ == "__main__":
    raise SystemExit(main())
