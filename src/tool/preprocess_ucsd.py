from __future__ import annotations

import argparse
from pathlib import Path

from _common import PROJECT_ROOT, add_common_args, run_dataset


CONFIGS = {
    "ped2": PROJECT_ROOT / "src" / "configs" / "ucsd_ped2.yaml",
    "ped1": PROJECT_ROOT / "src" / "configs" / "ucsd_ped1.yaml",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preprocess UCSD Ped1/Ped2 into the common SPEC 1 schema.")
    parser.add_argument("--ped", choices=sorted(CONFIGS), default="ped2", help="UCSD subset to process.")
    parser.add_argument("--config", default=None, help="Optional config override. If omitted, --ped selects a config.")
    add_common_args(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = Path(args.config) if args.config else CONFIGS[args.ped]
    return run_dataset(args, config_path)


if __name__ == "__main__":
    raise SystemExit(main())
