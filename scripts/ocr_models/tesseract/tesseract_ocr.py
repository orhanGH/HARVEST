#!/usr/bin/env python3

from pathlib import Path
import argparse
import csv

from PIL import Image, ImageOps
import pytesseract


def preprocess_image(path: Path, scale: float):
    image = Image.open(path)
    image = ImageOps.exif_transpose(image)
    image = image.convert("L")

    if scale != 1.0:
        w, h = image.size
        image = image.resize((int(w * scale), int(h * scale)))

    return image


def main():
    parser = argparse.ArgumentParser(
        description="OCR model stage: run Tesseract on regions produced by the parser stage."
    )
    parser.add_argument("--regions-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--lang", default="eng+fra")
    parser.add_argument("--psm", default="6")
    parser.add_argument("--scale", type=float, default=1.5)
    args = parser.parse_args()

    manifest_path = Path(args.regions_manifest)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    text_out = output_dir / "ocr_text.csv"
    words_out = output_dir / "ocr_words.csv"

    text_fields = [
        "source_image",
        "region_id",
        "region_type",
        "region_image",
        "ocr_text",
    ]

    word_fields = [
        "source_image",
        "region_id",
        "region_type",
        "region_image",
        "text",
        "conf",
        "left",
        "top",
        "width",
        "height",
    ]

    with manifest_path.open(newline="", encoding="utf-8") as mf, \
         text_out.open("w", newline="", encoding="utf-8") as tf, \
         words_out.open("w", newline="", encoding="utf-8") as wf:

        reader = csv.DictReader(mf)
        text_writer = csv.DictWriter(tf, fieldnames=text_fields)
        word_writer = csv.DictWriter(wf, fieldnames=word_fields)

        text_writer.writeheader()
        word_writer.writeheader()

        count = 0

        for region in reader:
            region_image = Path(region["region_image"])
            print(f"OCR: {region_image}")

            image = preprocess_image(region_image, args.scale)

            ocr_text = pytesseract.image_to_string(
                image,
                lang=args.lang,
                config=f"--psm {args.psm} -c preserve_interword_spaces=1",
            )

            text_writer.writerow({
                "source_image": region["source_image"],
                "region_id": region["region_id"],
                "region_type": region["region_type"],
                "region_image": region["region_image"],
                "ocr_text": ocr_text,
            })

            data = pytesseract.image_to_data(
                image,
                lang=args.lang,
                config=f"--psm {args.psm} -c preserve_interword_spaces=1",
                output_type=pytesseract.Output.DICT,
            )

            for i, txt in enumerate(data["text"]):
                txt = str(txt).strip()
                if not txt:
                    continue

                word_writer.writerow({
                    "source_image": region["source_image"],
                    "region_id": region["region_id"],
                    "region_type": region["region_type"],
                    "region_image": region["region_image"],
                    "text": txt,
                    "conf": data["conf"][i],
                    "left": data["left"][i],
                    "top": data["top"][i],
                    "width": data["width"][i],
                    "height": data["height"][i],
                })

            count += 1

    print("OCR stage done.")
    print(f"OCR text:  {text_out}")
    print(f"OCR words: {words_out}")
    print(f"Regions OCRed: {count}")


if __name__ == "__main__":
    main()
