"""Model-neutral records exchanged by modular pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x0: int
    y0: int
    x1: int
    y1: int

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.x0, self.y0, self.x1, self.y1)


@dataclass(slots=True)
class TableRegion:
    table_region_id: str
    document_id: str
    page_id: str
    bbox: BoundingBox
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_region_id": self.table_region_id,
            "document_id": self.document_id,
            "page_id": self.page_id,
            "bbox": self.bbox.to_tuple(),
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class LogicalTable:
    """Pure geometric grouping; title and table number are optional interpretation metadata."""

    logical_table_id: str
    document_id: str
    table_region_ids: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "logical_table_id": self.logical_table_id,
            "document_id": self.document_id,
            "table_region_ids": self.table_region_ids,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class Row:
    row_id: str
    table_region_id: str
    bbox: BoundingBox
    index: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "table_region_id": self.table_region_id,
            "bbox": self.bbox.to_tuple(),
            "index": self.index,
        }


@dataclass(slots=True)
class Column:
    column_id: str
    table_region_id: str
    bbox: BoundingBox
    index: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "column_id": self.column_id,
            "table_region_id": self.table_region_id,
            "bbox": self.bbox.to_tuple(),
            "index": self.index,
        }


@dataclass(slots=True)
class Cell:
    cell_id: str
    table_region_id: str
    row_id: str
    column_id: str
    bbox: BoundingBox

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "table_region_id": self.table_region_id,
            "row_id": self.row_id,
            "column_id": self.column_id,
            "bbox": self.bbox.to_tuple(),
        }


@dataclass(slots=True)
class OCRCharacter:
    symbol: str
    bbox: BoundingBox | None = None
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "bbox": self.bbox.to_tuple() if self.bbox else None,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class OCRResult:
    cell_id: str
    model: str
    raw_text: str
    characters: list[OCRCharacter] = field(default_factory=list)
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "model": self.model,
            "raw_text": self.raw_text,
            "characters": [character.to_dict() for character in self.characters],
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
