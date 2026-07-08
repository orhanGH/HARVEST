#!/usr/bin/env python3
"""
Chandra OCR wrapper.

Goal:
PNG images -> Markdown/JSON/HTML output.

Run only via GPU Slurm job.
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
        "TODO: implement Chandra wrapper after env/GPU smoke test. "
        "This file is the clean location for it."
    )

if __name__ == "__main__":
    main()
