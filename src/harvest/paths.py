"""Hierarchical run-artifact path organization for the modular pipeline.

``RunPaths`` centralizes where each pipeline stage reads/writes its
artifacts under a single run directory, so stages agree on layout without
hard-coding paths in multiple places.

Layout
------
```
<run_dir>/
  ingest/pages.jsonl
  preprocess/processed_pages.jsonl
  layout/regions.jsonl
  ocr/<model>/ocr_results.jsonl
  parsed/<model>/records.jsonl
  validated/<model>/records.jsonl
  validated/<model>/summary.json
  exports/<model>/<year>/
  benchmarks/<model>/metrics.json
```
"""

from __future__ import annotations

from pathlib import Path


class RunPaths:
    """Resolves artifact paths for a single pipeline run directory."""

    def __init__(self, run_dir: str | Path) -> None:
        self.run_dir = Path(run_dir)

    def stage_dir(self, *parts: str) -> Path:
        return self.run_dir.joinpath(*parts)

    # -- ingest ---------------------------------------------------------
    @property
    def ingest_dir(self) -> Path:
        return self.stage_dir("ingest")

    @property
    def pages_manifest(self) -> Path:
        return self.ingest_dir / "pages.jsonl"

    # -- preprocess -------------------------------------------------------
    @property
    def preprocess_dir(self) -> Path:
        return self.stage_dir("preprocess")

    @property
    def processed_manifest(self) -> Path:
        return self.preprocess_dir / "processed_pages.jsonl"

    # -- layout -----------------------------------------------------------
    @property
    def layout_dir(self) -> Path:
        return self.stage_dir("layout")

    @property
    def regions_manifest(self) -> Path:
        return self.layout_dir / "regions.jsonl"

    @property
    def cells_manifest(self) -> Path:
        return self.layout_dir / "cells.jsonl"

    @property
    def logical_tables_manifest(self) -> Path:
        return self.layout_dir / "logical_tables.jsonl"

    # -- ocr ----------------------------------------------------------------
    def ocr_dir(self, model: str) -> Path:
        return self.stage_dir("ocr", model)

    def ocr_results_manifest(self, model: str) -> Path:
        return self.ocr_dir(model) / "ocr_results.jsonl"

    # -- parsed ---------------------------------------------------------------
    def parsed_dir(self, model: str) -> Path:
        return self.stage_dir("parsed", model)

    def parsed_records_manifest(self, model: str) -> Path:
        return self.parsed_dir(model) / "records.jsonl"

    # -- validated --------------------------------------------------------------
    def validated_dir(self, model: str) -> Path:
        return self.stage_dir("validated", model)

    def validated_records_manifest(self, model: str) -> Path:
        return self.validated_dir(model) / "records.jsonl"

    def validation_summary(self, model: str) -> Path:
        return self.validated_dir(model) / "summary.json"

    # -- exports ------------------------------------------------------------------
    def export_dir(self, model: str, year: str) -> Path:
        return self.stage_dir("exports", model, year)

    # -- benchmarks -------------------------------------------------------------
    def benchmark_dir(self, model: str) -> Path:
        return self.stage_dir("benchmarks", model)

    def benchmark_metrics(self, model: str) -> Path:
        return self.benchmark_dir(model) / "metrics.json"

    def ensure(self, path: Path) -> Path:
        """Ensure ``path``'s parent directory exists and return ``path``."""
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
