"""Orchestration interface for modular HARVEST pipeline stages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ConfigLoader
from .paths import RunPaths


class HarvestPipeline:
    def __init__(self, config_path: str | Path) -> None:
        self.loader = ConfigLoader(config_path)
        self.config: dict[str, Any] = self.loader.load()
        run_dir = self.config.get("project", {}).get("run_dir", "runs/harvest")
        self.paths = RunPaths(self.loader.resolve_path(run_dir))

    def table_detection(self) -> Path:
        """Reserve the detected-table manifest for a future detection implementation."""
        self.paths.table_detection.mkdir(parents=True, exist_ok=True)
        return self.paths.detected_tables_manifest

    def table_structure(self) -> tuple[Path, Path, Path]:
        """Reserve row, column, and cell manifests for a future structure implementation."""
        self.paths.table_structure.mkdir(parents=True, exist_ok=True)
        return (
            self.paths.rows_manifest,
            self.paths.columns_manifest,
            self.paths.cells_manifest,
        )
