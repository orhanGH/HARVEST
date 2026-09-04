"""Generic record validation migrated from the legacy stage."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from harvest_ocr.utils import read_jsonl, write_json, write_jsonl


def validate_record(record: dict[str, Any], settings: dict[str, Any] | None = None) -> list[str]:
    settings = settings or {}
    flags: list[str] = []
    confidence = record.get("confidence")
    if confidence is not None and confidence < float(
        settings.get("review_confidence_threshold", 0.75)
    ):
        flags.append("low_ocr_confidence")

    numeric_fields = [
        key for key, value in record.items()
        if re.match(r"^(area|production|yield)(?:_.+)?$", key)
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    ]
    if not numeric_fields:
        flags.append("no_numeric_values")
    elif any(record[key] < 0 for key in numeric_fields):
        flags.append("negative_value")

    if settings.get("required_label_fields"):
        if not any(record.get(field) for field in settings["required_label_fields"]):
            flags.append("missing_country_label")
    elif "country_fr" in record or "country_en" in record:
        if not record.get("country_fr") and not record.get("country_en"):
            flags.append("missing_country_label")

    relative = float(settings.get("yield_relative_tolerance", 0.18))
    absolute = float(settings.get("yield_absolute_tolerance", 0.8))
    periods = {
        match.group(1)
        for key in record
        for match in [re.match(r"^(?:area|production|yield)_(.+)$", key)]
        if match
    }
    for period in periods:
        area = record.get(f"area_{period}")
        production = record.get(f"production_{period}")
        printed_yield = record.get(f"yield_{period}")
        if area not in (None, 0) and production is not None and printed_yield is not None:
            difference = abs(production / area - printed_yield)
            if difference > max(absolute, abs(printed_yield) * relative):
                flags.append(f"yield_mismatch_{period}")
    return flags


def validate_dataset(
    parsed_path: str | Path,
    validated_path: str | Path,
    summary_path: str | Path,
    settings: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    counts: Counter[str] = Counter()
    validated = []
    for record in read_jsonl(parsed_path):
        flags = validate_record(record, settings)
        output = dict(record)
        output["validation_flags"] = flags
        output["status"] = "review" if flags else "validated"
        counts.update(flags)
        validated.append(output)
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
