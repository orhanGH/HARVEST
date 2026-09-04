from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RunPaths:
    root: Path

    @property
    def preprocess_manifest(self) -> Path:
        return self.root / "preprocess" / "processed_pages.jsonl"

    @property
    def table_detection_manifest(self) -> Path:
        return self.root / "table_detection" / "detected_tables.jsonl"

    @property
    def table_structure_dir(self) -> Path:
        return self.root / "table_structure"
