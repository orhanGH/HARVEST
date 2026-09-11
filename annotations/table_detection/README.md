# Table-detection annotations

HARVEST evaluates table-detection predictions against small, manually labelled JSON or JSONL files.
Do **not** commit source PDF pages, rendered PNGs, or ad-hoc run outputs here.

## Coordinate convention

- Bounding boxes use `(x0, y0, x1, y1)` pixel coordinates.
- `x0, y0` is the top-left corner; `x1, y1` is the bottom-right corner.
- `pdf_page` is **one-based** and must match the PDF page numbers used by
  `scripts/table_detection/detect_tables_pdf.py`.
- Coordinates must be drawn in the same rendered page space used for inference, so record the render
  DPI and image dimensions with each page. The successful baseline used **180 DPI** on PDF pages
  **20-45**.

## Supported labels

- `table`
- `table rotated`

Keep raw labels exact in annotations and detector outputs. For localization evaluation, `table` and
`table rotated` are treated as equivalent when page number and IoU criteria match.

## Page-oriented format

Use either:

- one JSON object per line (`.jsonl`), or
- a `.json` file containing a top-level `pages` array or a direct array of page objects.

Each page object should look like:

```json
{
  "document_id": "0000765723_D0001",
  "pdf_page": 20,
  "image_width": 1530,
  "image_height": 2160,
  "dpi": 180,
  "annotations": [
    {
      "label": "table",
      "bbox": [120.0, 340.0, 1390.0, 1810.0],
      "annotator": "initials"
    }
  ]
}
```

Extra fields are preserved as metadata and ignored by the core IoU matching logic.

## How to create labels

1. Render candidate pages at the intended evaluation DPI (the default detector uses 180 DPI).
2. Draw boxes tightly around the visible table boundary.
3. Save one page record per labelled page in JSON or JSONL.
4. Record `image_width`, `image_height`, and optionally `dpi` so later reviewers can confirm the
   coordinate system.

## Evaluation workflow

Run the detector with `--annotations` to evaluate predictions against the labelled pages:

```bash
python scripts/table_detection/detect_tables_pdf.py \
  --pdf /absolute/path/to/document.pdf \
  --pages 20-45 \
  --dpi 180 \
  --threshold 0.50 \
  --annotations annotations/table_detection/my_labels.jsonl
```

The run writes:

- `detections.jsonl`: one normalized prediction per detected table;
- `pages.jsonl`: page metadata plus kept detections per page;
- `summary.json`: run-level counts and configuration;
- `evaluation.json`: true positives, false positives, false negatives, precision, recall, mean IoU,
  and per-page totals when annotations are supplied.

Post-processing includes a conservative scan-edge artifact filter (enabled by default): a detection
is removed only when its left edge is within `edge_margin_px` pixels of the page boundary (default
`5`) **and** `bbox_width / image_width` is at or below `edge_max_width_ratio` (default `0.05`). Use
`--no-edge-artifact-filter` to disable it.

Mean IoU is computed over matched prediction/annotation pairs only, and is reported as `0.0` when
no matches are found.
