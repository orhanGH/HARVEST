# HARVEST OCR

Reproducible extraction of tabular agricultural statistics from historical scanned yearbooks.
The pipeline preserves source images and raw OCR, assigns values by geometric column position,
normalizes the repeated area/production/yield schema, and flags uncertain rows for review.

## Pipeline

1. Extract the largest embedded page scan and the weak PDF OCR text layer.
2. Crop the paper, deskew, normalize illumination, and create OCR/layout views.
3. Detect the ruled table, printed rows, and only the target-year cell crops.
4. Run Tesseract, PaddleOCR, Chandra, or Surya behind a common JSONL interface.
5. Parse values without shifting columns when a printed cell is blank.
6. Validate `yield ≈ production / area` and create a review queue.
7. Compare models against a manually verified gold JSONL file.

The default configuration targets Table 7 (Wheat) through Table 40 (Raw Silk) in the supplied
1926 International Statistical Year-Book. It processes PDF pages 44-83 and exports only 1925.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[base,dev]'
```

Tesseract itself and the `eng`/`fra` language packs are system dependencies. The learned OCR
models are intentionally optional because they require separate, frequently incompatible GPU
environments.

For the optional Table Transformer detector baseline, install the PyTorch build that matches your
CPU/CUDA environment first, then install Transformers in that same environment:

```bash
pip install -e '.[dev]'
pip install 'transformers>=4.39'
```

## End-to-end Tesseract baseline

Copy the PDF to `data/0000765723_D0001.pdf`, then run:

```bash
harvest-ocr --config configs/harvest_1926.yaml run --model tesseract
```

Or execute individual, restartable stages:

```bash
harvest-ocr --config configs/harvest_1926.yaml extract
harvest-ocr --config configs/harvest_1926.yaml preprocess
harvest-ocr --config configs/harvest_1926.yaml layout
harvest-ocr --config configs/harvest_1926.yaml ocr --model tesseract
harvest-ocr --config configs/harvest_1926.yaml parse --model tesseract
harvest-ocr --config configs/harvest_1926.yaml validate --model tesseract
harvest-ocr --config configs/harvest_1926.yaml export --model tesseract
```

Outputs are stored under `runs/harvest_1926/`. The most useful artifacts are:

- `layout/debug/`: grid and row-detection overlays;
- `ocr/<model>/ocr_results.jsonl`: model-neutral raw OCR;
- `validated/<model>/records.jsonl`: normalized records and review flags;
- `validated/<model>/summary.json`: validation statistics.
- `exports/<model>/1925/`: one five-column CSV per product.

Each product CSV contains exactly `country_name_english`, `country_name_french`,
`area_hectares_1925`, `production_quintals_1925`, and `yield_per_hectare_1925`. Products whose
source table contains only production retain blank area and yield cells. Values printed in
thousands are converted to base units; Wool uses 10,000 quintals per printed unit and Raw Silk
uses 10 quintals per metric tonne.

## Learned OCR models

Use one environment per model. After the shared `extract`, `preprocess`, and `layout` stages:

```bash
harvest-ocr --config configs/harvest_1926.yaml ocr --model paddle
harvest-ocr --config configs/harvest_1926.yaml parse --model paddle
harvest-ocr --config configs/harvest_1926.yaml validate --model paddle
```

Replace `paddle` with `chandra` or `surya`. Paddle, Chandra, and Surya use table regions by
default; Tesseract uses cell regions. Their native outputs are retained alongside the common
JSONL output.

## Benchmarking

Create a manually corrected `gold.jsonl` using records from the validated output as templates.
Then run:

```bash
harvest-ocr --config configs/harvest_1926.yaml benchmark \
  --model tesseract --gold gold/gold.jsonl
```

The report includes row coverage, exact numeric-cell accuracy, per-field accuracy, and country
label similarity. A value recognized perfectly in the wrong column is counted as wrong.

## Table Transformer table-detection baseline

The detector baseline lives in `scripts/table_detection/detect_tables_pdf.py` and keeps bbox,
matching, annotation loading, and evaluation utilities in `src/harvest_ocr/table_detection.py`.
The successful baseline settings were:

- model: `microsoft/table-transformer-detection`
- labels kept: `table`, `table rotated`
- pages: `20-45`
- DPI: `180`
- confidence threshold: `0.50`

Example run:

```bash
python scripts/table_detection/detect_tables_pdf.py \
  --pdf /absolute/path/to/0000765723_D0001.pdf \
  --pages 20-45 \
  --dpi 180 \
  --threshold 0.50 \
  --bbox-padding 8
```

Optional flags:

- `--output-dir` to choose the run directory;
- `--device auto|cpu|cuda|cuda:0|mps`;
- `--annotations annotations/table_detection/labels.jsonl` to compute IoU-based evaluation against
  manual labels;
- `--save-page-renders` to retain rendered PNG pages for review.

Each run writes:

- `pages.jsonl`: one page record with image dimensions and kept detections;
- `detections.jsonl`: one normalized detection per table with `bbox` and padded `crop_bbox`;
- `summary.json`: run configuration, pages processed, counts before/after overlap filtering, and
  optional evaluation results;
- `evaluation.json`: precision/recall/mean-IoU summary when annotations are supplied.

Predictions are filtered to `table` and `table rotated`, clipped to image bounds, optionally padded
for safer downstream crops, and deduplicated deterministically before export.

See `annotations/table_detection/README.md` for the manual-label schema and evaluation workflow.
Keep generated page PNGs, PDFs, Hugging Face caches, and run outputs out of Git by using a path
under `runs/` (already ignored) or a directory outside the repository.

## Repository layout

```text
configs/                     document and table-layout configuration
annotations/table_detection/ manual table-detection labels and format notes
src/harvest_ocr/             reusable Python package
scripts/table_detection/     Table Transformer detector CLI
scripts/ocr_models/          model-specific command wrappers
scripts/pipeline/            repository-local pipeline entry point
scripts/postprocess/         validation helper
scripts/slurm/               Marvin CPU/GPU job templates
scripts/slurm/table_detection/ Slurm launcher for Table Transformer runs
tests/                       parser, validation, and layout tests
```

See `docs/IMPLEMENTATION.md` for the schema and operational details.

## Marvin Tesseract run

The Marvin job stages the PDF and all small intermediate PNG files on compute-node temporary
storage. Only final CSV/JSON outputs and one compressed diagnostics archive are copied back to
Lustre.

```bash
cd ~/project_harvest/HARVEST
bash scripts/marvin/setup_tesseract.sh
mkdir -p runs/slurm
sbatch scripts/slurm/run_marvin_tesseract.sbatch
```

The setup downloads the official `eng` and `fra` fast Tesseract language models into
`~/.local/share/harvest-tessdata`; the Slurm job sets `TESSDATA_PREFIX` to that directory.

By default, the job reads the PDF from
`$HARVEST_WORKSPACE/s6oraydi_work/old/data/0000765723_D0001.pdf` and writes versioned results to
`$HARVEST_WORKSPACE/s6oraydi_work/results/harvest_1926/tesseract/<job-id>/`. Override
`HARVEST_SOURCE_PDF` or `HARVEST_FINAL_ROOT` before `sbatch` if the source has moved.
