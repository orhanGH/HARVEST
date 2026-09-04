from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

BoundingBox = tuple[int, int, int, int]


@dataclass(slots=True)
class DetectedTable:
    table_region_id: str
    document_id: str
    page_id: str
    bbox: BoundingBox
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Row:
    row_id: str
    table_region_id: str
    row_index: int
    bbox: BoundingBox

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Column:
    column_id: str
    table_region_id: str
    column_index: int
    bbox: BoundingBox
    semantic_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Cell:
    cell_id: str
    table_region_id: str
    row_index: int
    column_index: int
    bbox: BoundingBox

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
