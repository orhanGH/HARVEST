from __future__ import annotations

from typing import Any

import numpy as np

from ...types import DetectedTable
from ...utils import HarvestError


def _cv2():
    try:
        import cv2
    except ImportError as exc:
        raise HarvestError("OpenCV is required for legacy table detection.") from exc
    return cv2


def _cluster_positions(values: list[int], tolerance: int) -> list[int]:
    if not values:
        return []
    merged: list[list[int]] = []
    for value in sorted(values):
        if merged and value - int(np.mean(merged[-1])) <= tolerance:
            merged[-1].append(value)
        else:
            merged.append([value])
    return [int(round(float(np.median(cluster)))) for cluster in merged]


def _line_segments(binary: np.ndarray, horizontal: bool) -> list[tuple[int, int, int, int]]:
    cv2 = _cv2()
    height, width = binary.shape[:2]
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (max(35, width // 12), 1) if horizontal else (1, max(25, height // 8)),
    )
    mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return [cv2.boundingRect(contour) for contour in contours]


def _detect_table_bbox(binary: np.ndarray, min_width_ratio: float) -> tuple[tuple[int, int, int, int], list[int]]:
    height, width = binary.shape[:2]
    long_lines = [
        line for line in _line_segments(binary, horizontal=True)
        if line[2] >= width * min_width_ratio
    ]
    if len(long_lines) < 2:
        return (int(width * 0.08), int(height * 0.08), int(width * 0.94), int(height * 0.72)), []
    usable = [line for line in long_lines if height * 0.04 <= line[1] <= height * 0.9]
    if len(usable) < 2:
        usable = long_lines
    ys = _cluster_positions([y + h // 2 for _, y, _, h in usable], max(2, height // 500))
    top_line, bottom_line = min(usable, key=lambda value: value[1]), max(usable, key=lambda value: value[1])
    return (
        max(0, min(line[0] for line in usable)),
        max(0, top_line[1]),
        min(width, max(line[0] + line[2] for line in usable)),
        min(height, bottom_line[1] + bottom_line[3]),
    ), ys


class LegacyOpenCVTableDetector:
    """Legacy morphology-based page-level table localizer."""

    def detect(self, page_image: np.ndarray, settings: dict[str, Any]) -> list[DetectedTable]:
        if page_image.ndim != 2:
            raise HarvestError("Legacy table detection requires a grayscale binary page image.")
        bbox, _ = _detect_table_bbox(page_image, float(settings.get("min_table_width_ratio", 0.65)))
        document_id = str(settings.get("document_id", "document"))
        page_id = str(settings.get("page_id", "page"))
        return [DetectedTable(
            table_region_id=str(settings.get("table_region_id", f"{page_id}-table-000")),
            document_id=document_id,
            page_id=page_id,
            bbox=bbox,
            confidence=1.0 if bbox else 0.0,
            metadata={"backend": "legacy_opencv"},
        )]
