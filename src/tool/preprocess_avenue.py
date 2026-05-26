from __future__ import annotations

import argparse
from pathlib import Path

from _common import PROJECT_ROOT, add_common_args, run_dataset


DEFAULT_CONFIG = PROJECT_ROOT / "src" / "configs" / "avenue.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preprocess CUHK Avenue into the common SPEC 1 schema.")
    parser.add_argument("--config", default=None, help="Optional config override. Defaults to src/configs/avenue.yaml.")
    add_common_args(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = Path(args.config) if args.config else DEFAULT_CONFIG
    return run_dataset(args, config_path)


if __name__ == "__main__":
    raise SystemExit(main())
