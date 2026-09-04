"""Command-line scaffold for the modular pipeline."""

from __future__ import annotations

import argparse

from .pipeline import HarvestPipeline


MODELS = ("effocr", "tesseract", "paddle", "chandra", "surya")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harvest")
    parser.add_argument("--config", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "detect-tables", aliases=["table-detection"],
        help="Detect table regions.",
    )
    commands.add_parser(
        "extract-structure", aliases=["table-structure"],
        help="Extract table rows, columns, and cells.",
    )
    ocr = commands.add_parser("ocr", help="Run an OCR backend (not implemented).")
    ocr.add_argument("--model", choices=MODELS, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    pipeline = HarvestPipeline(args.config)
    if args.command in ("detect-tables", "table-detection"):
        print(pipeline.table_detection())
    elif args.command in ("extract-structure", "table-structure"):
        print("\n".join(map(str, pipeline.table_structure())))
    else:
        raise NotImplementedError("OCR adapters have not moved to the modular scaffold.")
    return 0
