"""Orchestration for the implemented modular stages."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import load_config, resolve_project_path
from .modules.export import export_product_csvs
from .modules.ingest import extract_pdf_pages
from .modules.preprocess import preprocess_manifest
from .modules.validation import validate_dataset
from .paths import RunPaths
from .utils import HarvestError


class HarvestPipeline:
    def __init__(self, config_path: str | Path):
        self.config = load_config(config_path)
        configured = os.environ.get("HARVEST_RUN_DIR", self.config["project"]["run_dir"])
        self.run_dir = resolve_project_path(self.config, configured)
        self.paths = RunPaths(self.run_dir)

    def ingest(self) -> Path:
        configured = os.environ.get("HARVEST_INPUT_PDF", self.config["input"]["pdf"])
        return extract_pdf_pages(
            resolve_project_path(self.config, configured),
            self.paths.stage("ingest"),
            pages=str(self.config["input"].get("pages") or ""),
            document_id=self.config["project"].get("name"),
        )

    extract = ingest

    def preprocess(self) -> Path:
        if not self.paths.pages_manifest.exists():
            raise HarvestError("Missing pages manifest. Run the extract stage first.")
        return preprocess_manifest(
            self.paths.pages_manifest,
            self.paths.stage("preprocess"),
            self.config.get("preprocess", {}),
        )

    def table_detection(self) -> None:
        raise NotImplementedError("table_detection is scheduled for a later phase")

    def table_structure(self) -> None:
        raise NotImplementedError("table_structure is scheduled for a later phase")

    def validate(self, model: str | None = None) -> tuple[Path, Path]:
        model_dir = self.paths.root / "parsed" / model if model else self.paths.root / "parsed"
        parsed = model_dir / "records.jsonl"
        if not parsed.exists():
            raise HarvestError(f"Missing parsed output: {parsed}")
        output = self.paths.root / "validated" / model if model else self.paths.root / "validated"
        return validate_dataset(parsed, output / "records.jsonl", output / "summary.json", self.config.get("validation", {}))

    def export(self, model: str | None = None) -> Path:
        model_dir = self.paths.root / "validated" / model if model else self.paths.root / "validated"
        records = model_dir / "records.jsonl"
        if not records.exists():
            raise HarvestError(f"Missing validated output: {records}")
        catalog = self.config.get("table_catalog", self.config.get("parser", {}).get("table_catalog", []))
        output = self.paths.root / "exports" / model if model else self.paths.root / "exports"
        return export_product_csvs(records, output, catalog)
