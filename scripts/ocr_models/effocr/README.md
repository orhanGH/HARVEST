# EfficientOCR adapter for HARVEST

This adapter uses Melissa Dell and collaborators' EfficientOCR as the text
recognizer inside HARVEST. It targets the maintained Apache-2.0 implementation:

- source: <https://github.com/dell-research-harvard/efficient_ocr>
- verified upstream commit: `e38da3cd0b614cf13ba4c148bab5b37aeec3db7d`
- paper: <https://arxiv.org/abs/2304.02737>

## Why it is a separate pipeline

EfficientOCR localizes characters/words and recognizes them by image retrieval.
It does not recover table rows, columns, headers, or semantic field names.
HARVEST therefore supplies geometry-defined crops and keeps parsing and
validation separate:

1. render the PDF page;
2. locate the table and crop its cells;
3. run EfficientOCR on each cell crop;
4. assemble cells by `row_id` and `field`;
5. validate the numeric relationships;
6. export the HARVEST CSV.

For the recurring nine-value agricultural layout, crop the desired 1925 cells
directly (`area_1925`, `production_1925`, `yield_1925`). Do not OCR a whole row
and hope reading order preserves all nine numeric columns.

## Manifest contract

Input may be CSV, JSON, or JSONL. Each record must contain one image-path key:
`crop_path`, `image_path`, `path`, or `image`.

Recommended fields:

```json
{"region_id":"t07_p038_r001_area_1925","region_type":"cell","row_id":"t07_p038_r001","field":"area_1925","crop_path":"crops/t07_p038_r001_area_1925.png"}
```

Run a no-model contract check first:

```bash
python scripts/ocr_models/effocr/run_effocr_ocr.py \
  --regions-manifest runs/regions/cells.jsonl \
  --output-dir runs/effocr \
  --validate-only
```

Then run inference:

```bash
python scripts/ocr_models/effocr/run_effocr_ocr.py \
  --regions-manifest runs/regions/cells.jsonl \
  --output-dir runs/effocr \
  --model-dir models/effocr \
  --device cpu
```

The output is `effocr_raw.jsonl`. It retains the manifest metadata, recognized
text, and compact line/word geometry. It deliberately does not create the final
HARVEST CSV.

## Initial evaluation

Start with table 7 (Wheat), PDF pages 44-45, not the whole 192-page PDF. Manually
label 20-30 representative rows including digits, commas, decimal points,
asterisks, dashes, footnote markers, and accented French names. Compare:

- exact-cell accuracy for the three requested 1925 numeric fields;
- character error rate for French and English country names;
- complete-row accuracy;
- validation failure rate (`production / area` against yield when applicable).

Only after the small benchmark should we decide whether the pretrained model is
enough or whether to fine-tune the localizer/recognizer on HARVEST crops.
