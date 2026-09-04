"""Generic product export migrated from the legacy stage."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from harvest_ocr.utils import read_jsonl, safe_stem


def _display_number(value: Any) -> str:
    if value is None:
        return ""
    number = float(value)
    return str(int(number)) if number.is_integer() else format(number, ".12g")


def _columns(product: dict[str, Any], records: list[dict[str, Any]]) -> list[tuple[str, str]]:
    configured = product.get("columns") or product.get("output_columns")
    if configured:
        return [
            (str(item.get("header", item.get("name", item))), str(item.get("field", item.get("name", item))))
            if isinstance(item, dict) else (str(item), str(item))
            for item in configured
        ]
    if records and any(key in records[0] for key in ("country_en", "area_1925", "production_1925", "yield_1925")):
        return [
            ("country_name_english", "country_en"),
            ("area_hectares_1925", "area_1925"),
            ("production_quintals_1925", "production_1925"),
            ("yield_per_hectare_1925", "yield_1925"),
        ]
    keys = sorted({key for row in records for key in row if key not in {"product_id", "row_type"}})
    return [(key, key) for key in keys]


def export_product_csvs(
    records_path: str | Path,
    output_dir: str | Path,
    table_catalog: list[dict[str, Any]],
) -> Path:
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in read_jsonl(records_path):
        if record.get("row_type") in (None, "country"):
            product_id = record.get("product_id")
            if product_id:
                grouped[str(product_id)].append(record)
    for product in table_catalog:
        product_id = str(product["product_id"])
        rows = grouped.get(product_id, [])
        columns = _columns(product, rows)
        number = product.get("table_number", product_id)
        suffix = product.get("target_year")
        if suffix is None and any(field.endswith("_1925") for _, field in columns):
            suffix = "1925"
        suffix_text = f"_{safe_stem(str(suffix))}" if suffix is not None else ""
        output = target / f"table_{safe_stem(str(number))}_{safe_stem(product_id)}{suffix_text}.csv"
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[header for header, _ in columns])
            writer.writeheader()
            for row in rows:
                writer.writerow({header: _display_number(row.get(field)) if isinstance(row.get(field), (int, float)) else row.get(field, "") for header, field in columns})
    return target
