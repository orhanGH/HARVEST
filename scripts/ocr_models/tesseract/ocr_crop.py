#!/usr/bin/env python3

from pathlib import Path
import argparse
import csv
from PIL import Image, ImageOps
import pytesseract


META_FIELDS = [
    "product_id", "table_number", "product_fr", "product_en",
    "page_role", "sort_order",
    "source_image", "region_id", "region_image",
]


def preprocess(path: Path, scale: float):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("L")

    if scale != 1.0:
        w, h = img.size
        img = img.resize((int(w * scale), int(h * scale)))

    return img


def main():
    ap = argparse.ArgumentParser(description="OCR table crops with Tesseract.")
    ap.add_argument("--regions", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--lang", default="eng+fra")
    ap.add_argument("--psm", default="6")
    ap.add_argument("--scale", type=float, default=1.5)
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    text_csv = out_dir / "ocr_text.csv"
    words_csv = out_dir / "ocr_words.csv"

    text_fields = META_FIELDS + ["ocr_text"]

    word_fields = META_FIELDS + [
        "block_num", "par_num", "line_num", "word_num",
        "text", "conf",
        "left", "top", "width", "height",
        "scale",
    ]

    with Path(args.regions).open(newline="", encoding="utf-8") as rf, \
         text_csv.open("w", newline="", encoding="utf-8") as tf, \
         words_csv.open("w", newline="", encoding="utf-8") as wf:

        reader = csv.DictReader(rf)
        text_writer = csv.DictWriter(tf, fieldnames=text_fields)
        word_writer = csv.DictWriter(wf, fieldnames=word_fields)

        text_writer.writeheader()
        word_writer.writeheader()

        count = 0

        for row in reader:
            region_image = Path(row["region_image"])
            print(f"OCR: {row['region_id']} -> {region_image.name}")

            img = preprocess(region_image, args.scale)
            config = f"--psm {args.psm} -c preserve_interword_spaces=1"

            meta = {k: row.get(k, "") for k in META_FIELDS}

            text = pytesseract.image_to_string(
                img,
                lang=args.lang,
                config=config,
            )

            text_writer.writerow({**meta, "ocr_text": text})

            data = pytesseract.image_to_data(
                img,
                lang=args.lang,
                config=config,
                output_type=pytesseract.Output.DICT,
            )

            for i, txt in enumerate(data["text"]):
                txt = str(txt).strip()
                if not txt:
                    continue

                word_writer.writerow({
                    **meta,
                    "block_num": data["block_num"][i],
                    "par_num": data["par_num"][i],
                    "line_num": data["line_num"][i],
                    "word_num": data["word_num"][i],
                    "text": txt,
                    "conf": data["conf"][i],
                    "left": data["left"][i],
                    "top": data["top"][i],
                    "width": data["width"][i],
                    "height": data["height"][i],
                    "scale": args.scale,
                })

            count += 1

    print("OCR stage done.")
    print(f"Regions OCRed: {count}")
    print(f"OCR text:  {text_csv}")
    print(f"OCR words: {words_csv}")


if __name__ == "__main__":
    main()
