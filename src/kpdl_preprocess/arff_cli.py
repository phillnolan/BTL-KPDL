from __future__ import annotations

import argparse

from .arff import convert_csv_to_arff


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert feature CSV to WEKA ARFF.")
    parser.add_argument("--input", required=True, help="Input feature CSV.")
    parser.add_argument("--output", required=True, help="Output ARFF path.")
    parser.add_argument("--relation", default=None, help="Optional ARFF relation name.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = convert_csv_to_arff(args.input, args.output, args.relation)
    print(output)
    return 0
