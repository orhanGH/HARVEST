from __future__ import annotations

from typing import Protocol

import numpy as np

from ...types import DetectedTable


class TableDetector(Protocol):
    def detect(self, page_image: np.ndarray, settings: dict) -> list[DetectedTable]:
        """Locate table regions on one preprocessed page."""
