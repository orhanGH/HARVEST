# HARVEST implementation notes

## Stable interfaces

Every processing stage writes a JSONL manifest and never overwrites the preceding stage. Model
adapters produce the same `OCRResult` envelope:

```json
{
  "region_id": "page-0048-r012-c06",
  "source_model": "tesseract",
  "text": "10,193",
  "confidence": 0.94,
  "items": [],
  "raw_output_path": null,
  "error": null
}
```

`region_id` is the join key back to `regions.jsonl`, which contains the page, bounding box, row,
column index, and semantic column ID.

## Why values are position-based

Rows frequently contain dashes, ellipses, or entirely blank cells. HARVEST uses explicit
geometric ranges for the 1925 columns, so missing older-period values cannot shift the target
values into the wrong field.

## Internal target-year columns

```text
country_fr
area_1925 production_1925 yield_1925
country_en
```

The final per-product CSV contains English country, French country, area in hectares,
production in quintals, and yield per hectare for 1925 only. Raw text, missing codes, footnote
markers, bounding boxes, and confidence remain in JSONL so that extraction stays auditable.

## Review rules

Rows are sent to review when they have no country label, contain no numeric values, contain
negative values, fall below the OCR confidence threshold, or violate the loose printed
relationship `yield ≈ production / area`. Validation warns; it never silently changes values.

## Model isolation

PaddleOCR, Chandra, and Surya should not share one Conda environment. Their Paddle, Torch,
Transformers, vLLM, and CUDA constraints can conflict. Shared preprocessing output can be read by
all model environments, so only the adapter stage needs to run inside the specialized environment.
