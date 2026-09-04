from pathlib import Path

import pytest

from harvest.config import ConfigLoader


def test_load_missing_file_raises_file_not_found(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        ConfigLoader(tmp_path / "missing.yaml").load()


def test_resolve_path_handles_absolute_and_relative_paths(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}\n", encoding="utf-8")
    loader = ConfigLoader(config_path)
    loader.load()

    assert loader.resolve_path("runs/output") == tmp_path / "runs/output"
    assert loader.resolve_path(tmp_path / "absolute") == tmp_path / "absolute"
