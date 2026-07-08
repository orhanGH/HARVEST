#!/usr/bin/env python3
"""
PaddleOCR / PP-StructureV3 wrapper.

Goal:
PNG images -> Markdown/JSON output.

We will implement this after confirming PaddleOCR installation on Marvin.
"""
import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    raise SystemExit(
        "TODO: implement PaddleOCR wrapper after install smoke test. "
        "This file is the clean location for it."
    )

if __name__ == "__main__":
    main()
