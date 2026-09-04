import csv

from harvest.modules.export.writer import export_product_csvs
from harvest.utils import write_jsonl


def test_export_uses_configured_year_and_fields(tmp_path):
    records = tmp_path / "records.jsonl"
    write_jsonl(records, [{"product_id": "grain", "area_1937": 4, "production_1937": 20}])
    export_product_csvs(
        records,
        tmp_path / "exports",
        [{
            "table_number": "7",
            "product_id": "grain",
            "output_columns": [
                {"field": "area_1937", "header": "area_hectares_1937"},
                {"field": "production_1937", "header": "production_quintals_1937"},
            ],
            "filename_suffix": "1937",
        }],
    )
    path = tmp_path / "exports" / "table_7_grain_1937.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == ["area_hectares_1937", "production_quintals_1937"]
    assert rows == [{"area_hectares_1937": "4", "production_quintals_1937": "20"}]


def test_export_supports_completely_generic_fields(tmp_path):
    records = tmp_path / "records.jsonl"
    write_jsonl(records, [{"product_id": "grain", "measure_a": 1.5}])
    export_product_csvs(
        records,
        tmp_path / "exports",
        [{
            "table_number": "x",
            "product_id": "grain",
            "output": {
                "columns": [{"field": "measure_a", "header": "measure"}],
                "filename_template": "custom_{product_id}_{suffix}.csv",
                "filename_suffix": "edition",
            },
        }],
    )
    assert (tmp_path / "exports" / "custom_grain_edition.csv").exists()
