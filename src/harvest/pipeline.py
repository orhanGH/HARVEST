"""Pipeline orchestrator for the modular HARVEST refactor.

``HarvestPipeline`` exposes one method per stage (``extract``,
``preprocess``, ``layout``, ``ocr``, ``parse``, ``validate``, ``export``,
``benchmark``) plus a convenience ``run`` method that chains them.

This is Phase 1 scaffolding only: stage bodies raise ``NotImplementedError``.
Subsequent phases will migrate the actual stage logic from
``harvest_ocr`` into cell-/provenance-ID-based implementations here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import ConfigLoader
from .paths import RunPaths
from .utils import HarvestError


class HarvestPipeline:
    """Orchestrates the modular HARVEST pipeline stages for one config."""

    def __init__(self, config_path: str | Path) -> None:
        self.config = ConfigLoader(config_path)
        self.project_root = self.config.project_root
        configured_run_dir = os.environ.get(
            "HARVEST_RUN_DIR", str(self.config["project"]["run_dir"])
        )
        self.run_dir = self.config.resolve_path(configured_run_dir)
        self.paths = RunPaths(self.run_dir)

    def extract(self) -> Path:
        """Extract page scans and embedded text from the source PDF."""
        raise NotImplementedError("extract() is not yet implemented in src/harvest")

    def preprocess(self) -> Path:
        """Crop, deskew, normalize, and binarize extracted pages."""
        raise NotImplementedError("preprocess() is not yet implemented in src/harvest")

    def layout(self) -> Path:
        """Detect table geometry and emit table/row/column/cell records."""
        raise NotImplementedError("layout() is not yet implemented in src/harvest")

    def ocr(self, model: str, limit: int = 0, region_type: str | None = None) -> Path:
        """Run an OCR adapter over cell (or other region) images."""
        raise NotImplementedError("ocr() is not yet implemented in src/harvest")

    def parse(self, model: str) -> Path:
        """Normalize OCR output into typed, provenance-linked values."""
        raise NotImplementedError("parse() is not yet implemented in src/harvest")

    def validate(self, model: str) -> tuple[Path, Path]:
        """Apply consistency checks and emit validation issues."""
        raise NotImplementedError("validate() is not yet implemented in src/harvest")

    def export(self, model: str) -> Path:
        """Write target-year CSV products from validated records."""
        raise NotImplementedError("export() is not yet implemented in src/harvest")

    def benchmark(self, model: str, gold_path: str | Path) -> Path:
        """Compare validated output against a gold-standard JSONL file."""
        raise NotImplementedError("benchmark() is not yet implemented in src/harvest")

    def run(self, model: str, limit: int = 0) -> dict[str, Any]:
        """Run all stages in sequence for a single OCR model."""
        outputs: dict[str, Any] = {
            "pages": str(self.extract()),
            "processed": str(self.preprocess()),
            "regions": str(self.layout()),
            "ocr": str(self.ocr(model, limit=limit)),
            "parsed": str(self.parse(model)),
        }
        validated, summary = self.validate(model)
        outputs["validated"] = str(validated)
        outputs["validation_summary"] = str(summary)
        outputs["product_csvs"] = str(self.export(model))
        return outputs


__all__ = ["HarvestPipeline", "HarvestError"]
