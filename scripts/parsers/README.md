# HARVEST parsers

The OCR model output is not final data.

Each parser must produce the same schema:

product_id
table_number
image_filename
row_type
french_name
english_name
area_1925
production_1925
yield_1925
status
source_model
raw_source

Rules:

1. Keep country rows.
2. Keep continent totals as extra rows.
3. Keep world total if present.
4. Remove source/footnote/header rows.
5. Extract 1925 values by fixed position.

If a row has nine numeric values:

Area block:        n1 n2 n3
Production block:  n4 n5 n6
Yield block:       n7 n8 n9

Then:

area_1925       = n3
production_1925 = n6
yield_1925      = n9

No ratio-based column selection.
