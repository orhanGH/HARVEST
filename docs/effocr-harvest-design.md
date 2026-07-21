# HARVEST EfficientOCR design note

## Verified sources

The user-provided repository, `dell-research-harvard/effocr`, is the original
research implementation. The maintained implementation is
`dell-research-harvard/efficient_ocr`, verified at commit
`e38da3cd0b614cf13ba4c148bab5b37aeec3db7d` (2025-04-04), under Apache-2.0.

The paper's central idea is to replace sequence-to-sequence decoding with:

1. an object detector that localizes characters or words; and
2. a contrastively trained vision encoder that retrieves their identities.

This is attractive for HARVEST because it is sample-efficient to customize and
does not need a large language model. It is particularly suitable for isolated
numeric cells, where a language model can silently "correct" valid historical
values into wrong ones.

## Boundary between EffOCR and HARVEST

EfficientOCR owns glyph localization and recognition. HARVEST owns:

- PDF rendering and page selection;
- table and cell geometry;
- bilingual country-column association;
- table-specific year/measure mapping;
- numeric normalization and missing-value policy;
- validation, confidence flags, and CSV export.

This boundary is essential. The sample yearbook has two facing country-name
columns and up to nine numeric columns. A page-level OCR transcript cannot be
trusted to retain the correct row/column association.

## Target flow

```text
PDF -> page image -> table crop -> cell crops + manifest
    -> EfficientOCR raw JSONL -> geometry assembler
    -> deterministic field parser -> validator -> CSV + review queue
```

## Layout profiles

Two profiles are needed immediately:

1. `three_block_1925`: French name, English name, and the 1925 column from each
   of Area, Production, and Yield. Wheat is the reference example.
2. `annual_series_1925`: French name, English name, and one 1925 value. Raw Silk
   is the reference example; non-applicable area/yield fields stay empty.

Profiles should be selected from detected table metadata, never merely from a
fixed physical PDF page number.

## Staged adoption

1. Freeze a labeled Wheat benchmark (20-30 rows across both pages).
2. Run pretrained EfficientOCR on exact cell crops.
3. Compare it to the existing Tesseract/Paddle outputs at cell and row level.
4. Inspect confusion pairs (`0/O`, `1/l`, comma/period, dash, asterisk, footnote
   markers) and crop/localizer failures.
5. Fine-tune only if pretrained performance misses the acceptance threshold.
6. Add a second layout benchmark such as Raw Silk before scaling to tables 7-40.

## Acceptance gates

- 100% of exported rows preserve explicit page/table/row provenance.
- No value crosses a geometry-defined column boundary.
- Numeric parse failures and ambiguous glyphs enter the review queue.
- Complete-row accuracy is reported in addition to character error rate.
- Scaling begins only after the held-out benchmark meets the agreed threshold.
