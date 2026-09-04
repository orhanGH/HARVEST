from pathlib import Path

from harvest.paths import RunPaths


def test_run_paths_exposes_modular_directories(tmp_path: Path):
    paths = RunPaths(tmp_path / "run")

    assert paths.ingest == tmp_path / "run/ingest"
    assert paths.preprocess == tmp_path / "run/preprocess"
    assert paths.table_detection == tmp_path / "run/table_detection"
    assert paths.table_structure == tmp_path / "run/table_structure"
    assert paths.ocr == tmp_path / "run/ocr"
    assert paths.interpretation == tmp_path / "run/interpretation"
    assert paths.parsed == tmp_path / "run/parsed"
    assert paths.validated == tmp_path / "run/validated"
    assert paths.exports == tmp_path / "run/exports"


def test_run_paths_exposes_stage_manifests(tmp_path: Path):
    paths = RunPaths(tmp_path)

    assert paths.pages_manifest == tmp_path / "ingest/pages.jsonl"
    assert paths.processed_pages_manifest == tmp_path / "preprocess/processed_pages.jsonl"
    assert paths.detected_tables_manifest == tmp_path / "table_detection/detected_tables.jsonl"
    assert paths.logical_tables_manifest == tmp_path / "table_detection/logical_tables.jsonl"
    assert paths.rows_manifest == tmp_path / "table_structure/rows.jsonl"
    assert paths.columns_manifest == tmp_path / "table_structure/columns.jsonl"
    assert paths.cells_manifest == tmp_path / "table_structure/cells.jsonl"
