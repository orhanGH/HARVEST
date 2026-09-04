"""HARVEST modular table pipeline (Phase 1 scaffold).

This package is the target of an ongoing refactor of ``harvest_ocr`` into a
modular pipeline built around stable provenance IDs and lightweight
references between stages, instead of embedding whole upstream objects.

See ``docs/`` and the individual modules for design details:

- :mod:`harvest.types` -- expanded data model with provenance IDs.
- :mod:`harvest.config` -- YAML configuration loading.
- :mod:`harvest.paths` -- hierarchical run-artifact path organization.
- :mod:`harvest.utils` -- shared utilities.
- :mod:`harvest.pipeline` -- stage orchestrator (``HarvestPipeline``).
- :mod:`harvest.cli` -- command-line entry point.

Phase 1 provides the package scaffold and data model only; pipeline stage
bodies raise ``NotImplementedError`` until later phases migrate the actual
extraction/preprocessing/layout/OCR/parsing/validation/export logic from
``harvest_ocr``.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
