"""Configuration loading for the modular pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    def __init__(self, config_path: str | Path | None = None) -> None:
        self.config_path = Path(config_path).expanduser() if config_path else None
        self.project_root: Path | None = None

    def load(self, config_path: str | Path | None = None) -> dict[str, Any]:
        if config_path is not None:
            self.config_path = Path(config_path).expanduser()
        if self.config_path is None:
            raise ValueError("A configuration path is required.")
        path = self.config_path.resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        self.project_root = path.parent
        with path.open(encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}
        if not isinstance(config, dict):
            raise ValueError("Configuration root must be a mapping.")
        return config

    def resolve_path(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser()
        if candidate.is_absolute():
            return candidate
        base = self.project_root or (
            self.config_path.parent if self.config_path else Path.cwd()
        )
        return (base / candidate).resolve()
