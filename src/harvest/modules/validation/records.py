from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from harvest.utils import read_jsonl, write_json, write_jsonl


def _numeric_fields(settings: dict[str, Any]) -> list[str]:
    fields = settings.get("numeric_fields", [])
    return [str(field) for field in fields]


def validate_record(record: dict[str, Any], settings: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    label_fields = settings.get("label_fields", [])
    if label_fields and not any(record.get(field) for field in label_fields):
        flags.append("missing_label")

    numeric_fields = _numeric_fields(settings)
    present = [field for field in numeric_fields if record.get(field) is not None]
    if numeric_fields and not present:
        flags.append("no_numeric_values")
    if any(record[field] < 0 for field in present):
        flags.append("negative_value")

    confidence = record.get("confidence")
    threshold = float(settings.get("review_confidence_threshold", 0.75))
    if confidence is not None and confidence < threshold:
        flags.append("low_ocr_confidence")

    relations = settings.get("yield_relations", [])
    relative = float(settings.get("yield_relative_tolerance", 0.18))
    absolute = float(settings.get("yield_absolute_tolerance", 0.8))
    for relation in relations:
        area_field, production_field, yield_field = (
            relation["area"],
            relation["production"],
            relation["yield"],
        )
        area = record.get(area_field)
        production = record.get(production_field)
        printed = record.get(yield_field)
        if area not in (None, 0) and production is not None and printed is not None:
            if abs(production / area - printed) > max(absolute, abs(printed) * relative):
                flags.append(str(relation.get("flag", "yield_mismatch")))
    return flags


def validate_dataset(
    parsed_path: str | Path,
    validated_path: str | Path,
    summary_path: str | Path,
    settings: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    settings = settings or {}
    validated = []
    counts: Counter[str] = Counter()
    for record in read_jsonl(parsed_path):
        flags = validate_record(record, settings)
        record["validation_flags"] = flags
        record["status"] = "review" if flags else "validated"
        counts.update(flags)
        validated.append(record)
    write_jsonl(validated_path, validated)
    write_json(
        summary_path,
        {
            "records": len(validated),
            "validated": sum(row["status"] == "validated" for row in validated),
            "review": sum(row["status"] == "review" for row in validated),
            "flag_counts": dict(counts.most_common()),
        },
    )
    return Path(validated_path), Path(summary_path)
