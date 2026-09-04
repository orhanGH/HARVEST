"""Run artifact locations for the modular pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RunPaths:
    root: Path

    @property
    def ingest(self) -> Path:
        return self.root / "ingest"

    @property
    def preprocess(self) -> Path:
        return self.root / "preprocess"

    @property
    def table_detection(self) -> Path:
        return self.root / "table_detection"

    @property
    def table_structure(self) -> Path:
        return self.root / "table_structure"

    @property
    def ocr(self) -> Path:
        return self.root / "ocr"

    @property
    def interpretation(self) -> Path:
        return self.root / "interpretation"

    @property
    def parsed(self) -> Path:
        return self.root / "parsed"

    @property
    def validated(self) -> Path:
        return self.root / "validated"

    @property
    def exports(self) -> Path:
        return self.root / "exports"

    @property
    def pages_manifest(self) -> Path:
        return self.ingest / "pages.jsonl"

    @property
    def processed_pages_manifest(self) -> Path:
        return self.preprocess / "processed_pages.jsonl"

    @property
    def detected_tables_manifest(self) -> Path:
        return self.table_detection / "detected_tables.jsonl"

    @property
    def logical_tables_manifest(self) -> Path:
        return self.table_detection / "logical_tables.jsonl"

    @property
    def rows_manifest(self) -> Path:
        return self.table_structure / "rows.jsonl"

    @property
    def columns_manifest(self) -> Path:
        return self.table_structure / "columns.jsonl"

    @property
    def cells_manifest(self) -> Path:
        return self.table_structure / "cells.jsonl"

    def create_directories(self) -> None:
        for path in (
            self.ingest, self.preprocess, self.table_detection, self.table_structure,
            self.ocr, self.interpretation, self.parsed, self.validated, self.exports,
        ):
            path.mkdir(parents=True, exist_ok=True)
