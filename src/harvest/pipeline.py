from __future__ import annotations

from pathlib import Path
from typing import Any

from .modules.table_detection import LegacyOpenCVTableDetector
from .modules.table_structure import LegacyRulesTableStructureRecognizer
from .paths import RunPaths
from .types import DetectedTable
from .utils import HarvestError, parse_page_range, read_jsonl, write_jsonl


def _load_config(path: str | Path) -> dict[str, Any]:
    from harvest_ocr.utils import load_config
    return load_config(path)


class HarvestPipeline:
    """Modular geometry stages over the existing preprocessing artifacts."""

    def __init__(self, config_path: str | Path) -> None:
        self.config = _load_config(config_path)
        self.paths = RunPaths(Path(self.config["project"]["run_dir"]))

    @staticmethod
    def _page_settings(settings: dict[str, Any], page_number: int) -> dict[str, Any]:
        merged = {key: value for key, value in settings.items() if key != "page_profiles"}
        for profile in settings.get("page_profiles", []):
            if page_number in parse_page_range(str(profile["pages"])):
                merged.update({key: value for key, value in profile.items() if key != "pages"})
                break
        return merged

    def detect_tables(self) -> Path:
        if not self.paths.preprocess_manifest.exists():
            raise HarvestError("Missing processed page manifest. Run preprocess first.")
        import cv2
        detector = LegacyOpenCVTableDetector()
        tables = []
        for page in read_jsonl(self.paths.preprocess_manifest):
            image = cv2.imread(page["binary_image"], cv2.IMREAD_GRAYSCALE)
            if image is None:
                raise HarvestError(f"Could not load preprocessed page {page['pdf_page']}")
            page_number = int(page["pdf_page"])
            page_id = f"{page['document_id']}-page-{page_number:04d}"
            settings = self._page_settings(self.config.get("layout", {}), page_number)
            settings.update({"document_id": page["document_id"], "page_id": page_id, "table_region_id": f"{page_id}-table-000"})
            table = detector.detect(image, settings)[0]
            table.metadata["binary_image"] = page["binary_image"]
            tables.append(table)
        return write_jsonl(self.paths.table_detection_manifest, tables)

    def extract_structure(self) -> Path:
        if not self.paths.table_detection_manifest.exists():
            raise HarvestError("Missing detected tables manifest. Run table detection first.")
        import cv2
        recognizer = LegacyRulesTableStructureRecognizer()
        rows, columns, cells = [], [], []
        for item in read_jsonl(self.paths.table_detection_manifest):
            table = DetectedTable(
                table_region_id=item["table_region_id"], document_id=item["document_id"],
                page_id=item["page_id"], bbox=tuple(item["bbox"]), confidence=float(item["confidence"]),
                metadata=item.get("metadata", {}),
            )
            image_path = table.metadata.get("binary_image")
            image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE) if image_path else None
            if image is None:
                raise HarvestError(f"Detected table {table.table_region_id} has no readable binary_image reference.")
            page_number = int(table.page_id.rsplit("-", 1)[-1])
            extracted = recognizer.extract(table, image, self._page_settings(self.config.get("layout", {}), page_number))
            rows.extend(extracted[0]); columns.extend(extracted[1]); cells.extend(extracted[2])
        directory = self.paths.table_structure_dir
        write_jsonl(directory / "rows.jsonl", rows)
        write_jsonl(directory / "columns.jsonl", columns)
        write_jsonl(directory / "cells.jsonl", cells)
        return directory

    table_detection = detect_tables
    table_structure = extract_structure
