#!/usr/bin/env python3
"""
Surya OCR wrapper.

Goal:
PNG images -> OCR/layout/table output.

Try after Paddle and Chandra because Surya backend setup may be heavier.
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
        "TODO: implement Surya wrapper after backend compatibility check."
    )

if __name__ == "__main__":
    main()
