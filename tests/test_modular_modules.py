import csv

import numpy as np

from harvest.modules.export import export_product_csvs
from harvest.modules.preprocess import adaptive_binary, detect_paper_box
from harvest.modules.validation import validate_record
from harvest_ocr.utils import write_jsonl


def test_modular_preprocess_handles_synthetic_page():
    image = np.full((80, 120), 255, dtype=np.uint8)
    image[20:60, 30:90] = 0
    assert detect_paper_box(image)[2:] == (120, 80)
    binary = adaptive_binary(image)
    assert binary.shape == image.shape


def test_modular_validation_is_generic_and_flags_mismatch():
    record = {"label": "Example", "area_2024": 10, "production_2024": 100, "yield_2024": 2}
    flags = validate_record(record, {})
    assert "yield_mismatch_2024" in flags


def test_modular_export_uses_catalog_columns(tmp_path):
    records = tmp_path / "records.jsonl"
    write_jsonl(records, [{"product_id": "demo", "name": "A", "value": 12.5}])
    output = export_product_csvs(
        records,
        tmp_path / "exports",
        [{"product_id": "demo", "table_number": "1", "columns": [
            {"header": "Name", "field": "name"},
            {"header": "Value", "field": "value"},
        ]}],
    )
    with (output / "table_1_demo.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [{"Name": "A", "Value": "12.5"}]
