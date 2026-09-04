from __future__ import annotations

import argparse
import json

from .pipeline import HarvestPipeline
from .utils import HarvestError

MODELS = ("effocr", "tesseract", "paddle", "chandra", "surya")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harvest")
    parser.add_argument("--config", default="configs/harvest_1926.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("extract", "preprocess", "table-detection", "table-structure"):
        commands.add_parser(name)
    for name in ("validate", "export"):
        command = commands.add_parser(name)
        command.add_argument("--model", choices=MODELS, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        pipeline = HarvestPipeline(args.config)
        result = {
            "extract": pipeline.extract,
            "preprocess": pipeline.preprocess,
            "table-detection": pipeline.table_detection,
            "table-structure": pipeline.table_structure,
            "validate": lambda: pipeline.validate(args.model),
            "export": lambda: pipeline.export(args.model),
        }[args.command]()
        print(json.dumps([str(item) for item in result]) if isinstance(result, tuple) else result)
        return 0
    except (HarvestError, NotImplementedError) as exc:
        print(f"HARVEST error: {exc}")
        return 2
