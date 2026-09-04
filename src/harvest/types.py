"""Data model for the modular HARVEST pipeline.

This module defines the expanded data model used by ``src/harvest``. Unlike
the legacy ``harvest_ocr`` model, every artifact in this model carries a
stable, deterministic *provenance ID* so downstream stages can reference
upstream artifacts without embedding whole copies of them. Where a stage
needs to point at another artifact, it stores a lightweight reference (the ID
string) rather than a nested object.

Provenance ID chain
--------------------
``document_id`` -> ``page_id`` -> ``table_region_id`` -> ``logical_table_id``
                                -> ``row_id`` -> ``column_id`` -> ``cell_id``

Legacy compatibility types (``PageRecord``, ``ProcessedPage``, ``RegionRecord``,
``OCRItem`` and the legacy ``OCRResult`` shape) from ``harvest_ocr.types`` are
retained here, aliased, so existing code and tests can migrate incrementally.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Primitive geometry types
# ---------------------------------------------------------------------------

BBox = tuple[int, int, int, int]


@dataclass(slots=True)
class BoundingBox:
    """Axis-aligned pixel bounding box, ``(x0, y0, x1, y1)``."""

    x0: int
    y0: int
    x1: int
    y1: int

    def as_tuple(self) -> BBox:
        return (self.x0, self.y0, self.x1, self.y1)

    @classmethod
    def from_tuple(cls, value: BBox) -> "BoundingBox":
        x0, y0, x1, y1 = value
        return cls(x0=int(x0), y0=int(y0), x1=int(x1), y1=int(y1))

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Provenance-carrying core entities
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Cell:
    """Geometry-only description of a single table cell.

    ``Cell`` deliberately holds no OCR text: it only records *where* the
    cell is and *which* row/column it belongs to. Recognized text lives in a
    separate :class:`OCRResult` keyed by ``cell_id``.
    """

    cell_id: str
    document_id: str
    page_id: str
    table_region_id: str
    row_id: str
    column_id: str
    bbox: BoundingBox
    row_index: int
    column_index: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["bbox"] = self.bbox.as_tuple()
        return result


@dataclass(slots=True)
class OCRCharacter:
    """A single recognized character/symbol with its own geometry.

    Character-level data preserves punctuation and symbols (dashes, dots,
    asterisks, parentheses, etc.) that word- or line-level OCR output may
    otherwise normalize away.
    """

    text: str
    confidence: float | None = None
    bbox: BoundingBox | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.bbox is not None:
            result["bbox"] = self.bbox.as_tuple()
        return result


@dataclass(slots=True)
class OCRResult:
    """Recognized text for one cell (or other region), by provenance ID.

    ``raw_text`` is the verbatim recognizer output. ``characters`` is
    optional, fine-grained per-character data used to reconstruct symbols
    that whitespace-normalized text loses.
    """

    cell_id: str
    source_model: str
    raw_text: str
    confidence: float | None = None
    characters: list[OCRCharacter] = field(default_factory=list)
    raw_output_path: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["characters"] = [char.to_dict() for char in self.characters]
        return result


@dataclass(slots=True)
class LogicalTable:
    """A semantic table formed from one or more physical table regions.

    A logical table may span multiple pages or multiple detected regions on
    the same page (e.g. a table continued in a second column). It stores only
    the IDs of its constituent ``table_region_id`` values, never the region
    objects themselves.
    """

    logical_table_id: str
    document_id: str
    table_region_ids: list[str] = field(default_factory=list)
    table_number: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ColumnSemantic:
    """Maps a physical ``column_id`` to a semantic field name/type."""

    column_id: str
    logical_table_id: str
    field_name: str
    value_type: str = "text"
    unit: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ParsedValue:
    """A parsed, typed value for one cell, referenced by ID only."""

    cell_id: str
    row_id: str
    column_id: str
    field_name: str
    raw_text: str
    value: Any = None
    value_type: str = "text"
    parse_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationIssue:
    """A single validation finding, referencing the artifact it concerns."""

    issue_id: str
    severity: str  # e.g. "error", "warning", "info"
    code: str
    message: str
    document_id: str | None = None
    row_id: str | None = None
    column_id: str | None = None
    cell_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Legacy compatibility types (mirrors of harvest_ocr.types)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PageRecord:
    """Legacy page-extraction record. Retained for backward compatibility."""

    document_id: str
    pdf_path: str
    pdf_page: int
    printed_page: str | None
    image_path: str
    embedded_text_path: str | None
    width: int
    height: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProcessedPage:
    """Legacy preprocessing record. Retained for backward compatibility."""

    document_id: str
    pdf_page: int
    source_image: str
    layout_image: str
    ocr_image: str
    binary_image: str
    width: int
    height: int
    crop_box: BBox
    rotation_degrees: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RegionRecord:
    """Legacy layout-region record. Retained for backward compatibility."""

    region_id: str
    document_id: str
    pdf_page: int
    region_type: str
    region_image: str
    source_image: str
    bbox: BBox
    table_bbox: BBox
    row_index: int | None = None
    column_index: int | None = None
    column_id: str | None = None
    table_number: str | None = None
    page_role: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OCRItem:
    """Legacy OCR sub-item. Retained for backward compatibility."""

    text: str
    confidence: float | None = None
    bbox: BBox | None = None
    row_index: int | None = None
    column_index: int | None = None
    block_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LegacyOCRResult:
    """Legacy region-keyed OCR result. Retained for backward compatibility.

    This mirrors ``harvest_ocr.types.OCRResult`` (keyed by ``region_id`` and
    holding embedded ``items``). The new pipeline instead uses the
    cell-keyed :class:`OCRResult` defined above.
    """

    region_id: str
    source_model: str
    text: str
    confidence: float | None
    items: list[OCRItem] = field(default_factory=list)
    raw_output_path: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["items"] = [item.to_dict() for item in self.items]
        return result


def path_str(path: str | Path) -> str:
    return str(Path(path).resolve())
