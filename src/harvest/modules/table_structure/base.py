from __future__ import annotations

from typing import Protocol

import numpy as np

from ...types import Cell, Column, DetectedTable, Row


class TableStructureRecognizer(Protocol):
    def extract(
        self, detected_table: DetectedTable, page_image: np.ndarray, settings: dict
    ) -> tuple[list[Row], list[Column], list[Cell]]:
        """Extract geometry from a previously detected table region."""
