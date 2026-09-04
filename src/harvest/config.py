"""Configuration loading for the modular HARVEST pipeline.

Wraps YAML configuration loading behind a small ``ConfigLoader`` class so
pipeline stages depend on a stable interface rather than raw dict access
scattered across the codebase.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .utils import HarvestError


class ConfigLoader:
    """Loads and resolves a HARVEST YAML configuration file.

    Parameters
    ----------
    config_path:
        Path to a YAML configuration file, e.g. ``configs/harvest_1926.yaml``.
    """

    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path).resolve()
        if not self.config_path.exists():
            raise HarvestError(f"Config file not found: {self.config_path}")
        with self.config_path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise HarvestError(f"Config file must contain a mapping: {self.config_path}")
        self._data: dict[str, Any] = data
        # Project root is assumed to be the parent of the config's directory
        # (e.g. `configs/harvest_1926.yaml` -> repository root).
        self.project_root = self.config_path.parent.parent

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def section(self, key: str) -> dict[str, Any]:
        """Return a sub-mapping, defaulting to an empty dict."""
        value = self._data.get(key, {})
        if not isinstance(value, dict):
            raise HarvestError(f"Config section {key!r} must be a mapping")
        return value

    def resolve_path(self, value: str | Path) -> Path:
        """Resolve a possibly-relative path against the project root."""
        path = Path(value)
        if path.is_absolute():
            return path
        return self.project_root / path

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)
