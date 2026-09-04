from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from harvest.utils import read_jsonl, safe_stem


def _display_number(value: Any) -> str:
    if value is None:
        return ""
    number = float(value)
    return str(int(number)) if number.is_integer() else format(number, ".12g")


def _output_metadata(
    product: dict[str, Any], export_config: dict[str, Any] | None
) -> dict[str, Any]:
    metadata = dict(export_config or {})
    for key in ("output", "export"):
        if isinstance(product.get(key), dict):
            metadata.update(product[key])
    for key in ("output_columns", "filename_template", "filename_suffix", "row_type"):
        if key in product:
            metadata[key] = product[key]
    columns = metadata.get("columns", metadata.get("output_columns"))
    if not columns:
        raise ValueError("export metadata must define output columns")
    normalized = []
    for column in columns:
        if isinstance(column, str):
            normalized.append({"field": column, "header": column})
        elif isinstance(column, dict) and column.get("field") and column.get("header"):
            normalized.append(column)
        else:
            raise ValueError("each output column must define field and header")
    metadata["columns"] = normalized
    return metadata


def _filename(product: dict[str, Any], metadata: dict[str, Any]) -> str:
    product_id = safe_stem(str(product["product_id"]))
    values = {
        "table_number": product.get("table_number", ""),
        "product_id": product_id,
        "suffix": metadata.get("filename_suffix", ""),
    }
    template = metadata.get("filename_template")
    if template:
        return str(template).format(**values)
    suffix = str(values["suffix"])
    suffix = f"_{suffix}" if suffix else ""
    return f"table_{values['table_number']}_{product_id}{suffix}.csv"


def export_product_csvs(
    records_path: str | Path,
    output_dir: str | Path,
    table_catalog: Iterable[dict[str, Any]],
    export_config: dict[str, Any] | None = None,
) -> Path:
    """Write configured CSV files without assuming a particular schema or year."""
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    catalog = list(table_catalog)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    row_type_by_product: dict[str, Any] = {}
    for product in catalog:
        metadata = _output_metadata(product, export_config)
        row_type_by_product[str(product["product_id"])] = metadata.get("row_type")
    for record in read_jsonl(records_path):
        product_id = record.get("product_id")
        if not product_id or product_id not in row_type_by_product:
            continue
        row_type = row_type_by_product[str(product_id)]
        if row_type is not None and record.get("row_type") != row_type:
            continue
        grouped[str(product_id)].append(record)

    for product in catalog:
        metadata = _output_metadata(product, export_config)
        columns = metadata["columns"]
        output = target / _filename(product, metadata)
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[c["header"] for c in columns])
            writer.writeheader()
            for record in grouped.get(str(product["product_id"]), []):
                writer.writerow(
                    {
                        column["header"]: _display_number(record.get(column["field"]))
                        if record.get(column["field"]) is not None
                        else ""
                        for column in columns
                    }
                )
    return target
