from __future__ import annotations

import argparse

from .pipeline import HarvestPipeline
from .utils import HarvestError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harvest")
    parser.add_argument("--config", default="configs/harvest_1926.yaml")
    stages = parser.add_subparsers(dest="command", required=True)
    stages.add_parser("table-detection")
    stages.add_parser("table-structure")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        pipeline = HarvestPipeline(args.config)
        print(pipeline.detect_tables() if args.command == "table-detection" else pipeline.extract_structure())
        return 0
    except HarvestError as exc:
        print(f"HARVEST error: {exc}")
        return 2
