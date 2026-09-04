from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ...types import Cell, Column, DetectedTable, Row
from ...utils import HarvestError
from ..table_detection.legacy_opencv import _cluster_positions, _line_segments


@dataclass(slots=True)
class TableGeometry:
    bbox: tuple[int, int, int, int]
    header_bottom: int
    x_boundaries: list[int]
    column_ranges: list[tuple[int, int]]
    row_boundaries: list[tuple[int, int]]
    confidence: float


def _detect_x_boundaries(
    binary: np.ndarray, table_bbox: tuple[int, int, int, int], expected_count: int, fallback: list[float]
) -> tuple[list[int], float]:
    x0, y0, x1, y1 = table_bbox
    crop = binary[y0:y1, x0:x1]
    positions = [x + w // 2 for x, _, w, h in _line_segments(crop, horizontal=False) if h >= crop.shape[0] * 0.18]
    absolute = [x0 + value for value in _cluster_positions(positions, max(3, crop.shape[1] // 250)) if crop.shape[1] * .01 < value < crop.shape[1] * .99]
    candidates = _cluster_positions([x0, *absolute, x1], max(3, crop.shape[1] // 250))
    if len(candidates) == expected_count:
        return candidates, 1.0
    fallback_positions = [x0 + int(round((x1 - x0) * fraction)) for fraction in fallback]
    if len(fallback_positions) != expected_count:
        raise HarvestError(f"Expected {expected_count} fallback boundaries but got {len(fallback_positions)}")
    snap_distance = (x1 - x0) * .025
    snapped = [min((value for value in candidates if abs(value - fallback_x) <= snap_distance), key=lambda value: abs(value - fallback_x), default=fallback_x) for fallback_x in fallback_positions]
    for index in range(1, len(snapped)):
        snapped[index] = max(snapped[index], snapped[index - 1] + 2)
    return snapped, max(.35, 1.0 - abs(len(candidates) - expected_count) / expected_count)


def _detect_column_ranges(binary: np.ndarray, table_bbox: tuple[int, int, int, int], fallback_ranges: list[list[float]]) -> tuple[list[tuple[int, int]], list[int], float]:
    x0, y0, x1, y1 = table_bbox
    crop = binary[y0:y1, x0:x1]
    detected = [x0 + x + w // 2 for x, _, w, h in _line_segments(crop, horizontal=False) if h >= crop.shape[0] * .18]
    candidates = _cluster_positions([x0, *_cluster_positions(detected, max(3, crop.shape[1] // 250)), x1], max(3, crop.shape[1] // 250))
    snap_distance = (x1 - x0) * .035
    ranges, snapped_count = [], 0
    for pair in fallback_ranges:
        if len(pair) != 2 or not 0 <= float(pair[0]) < float(pair[1]) <= 1:
            raise HarvestError(f"Invalid normalized column range: {pair!r}")
        raw = [x0 + int(round((x1 - x0) * float(value))) for value in pair]
        snapped = [min((value for value in candidates if abs(value - position) <= snap_distance), key=lambda value: abs(value - position), default=position) for position in raw]
        snapped_count += sum(value != position for value, position in zip(snapped, raw))
        ranges.append((snapped[0], max(snapped[0] + 2, snapped[1])))
    confidence = max(.45, min(1.0, .55 + .45 * snapped_count / max(1, len(ranges) * 2)))
    return ranges, sorted({value for pair in ranges for value in pair}), confidence


def _header_bottom(table_bbox: tuple[int, int, int, int], horizontal_ys: list[int]) -> int:
    _, y0, _, y1 = table_bbox
    candidates = [y for y in horizontal_ys if y0 + (y1 - y0) * .08 < y < y0 + (y1 - y0) * .42]
    return max(candidates) if candidates else y0 + int((y1 - y0) * .22)


def _detect_rows(binary: np.ndarray, table_bbox: tuple[int, int, int, int], header_bottom: int, merge_factor: float) -> list[tuple[int, int]]:
    import cv2
    x0, _, x1, y1 = table_bbox
    crop = binary[header_bottom:y1, x0:x1]
    if not crop.size:
        return []
    horizontal = cv2.morphologyEx(crop, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(35, crop.shape[1] // 12), 1)))
    vertical = cv2.morphologyEx(crop, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, crop.shape[0] // 8))))
    projection = np.count_nonzero(cv2.subtract(crop, cv2.bitwise_or(horizontal, vertical)), axis=1)
    active = projection > max(20, int(np.percentile(projection, 60)))
    bands, start = [], None
    for y, is_active in enumerate(active):
        if is_active and start is None: start = y
        elif not is_active and start is not None: bands.append((start, y)); start = None
    if start is not None: bands.append((start, len(active)))
    merged = []
    for band in bands:
        if merged and band[0] - merged[-1][1] <= max(1, int(2 * merge_factor)): merged[-1] = (merged[-1][0], band[1])
        else: merged.append(band)
    centers = [header_bottom + (a + b) // 2 for a, b in merged if 2 <= b - a <= crop.shape[0] * .10]
    if len(centers) > 1: centers = _cluster_positions(centers, max(2, int(round(float(np.median(np.diff(centers))) * .65))))
    return [(header_bottom if i == 0 else int(round((centers[i - 1] + center) / 2)), y1 if i == len(centers) - 1 else int(round((center + centers[i + 1]) / 2))) for i, center in enumerate(centers)]


class LegacyRulesTableStructureRecognizer:
    """Legacy rule and projection based structure extraction."""

    def extract(self, detected_table: DetectedTable, page_image: np.ndarray, settings: dict[str, Any]) -> tuple[list[Row], list[Column], list[Cell]]:
        x0, y0, x1, y1 = detected_table.bbox
        columns_setting = settings.get("expected_column_count", settings.get("expected_columns"))
        expected_count = int(columns_setting) if isinstance(columns_setting, int) else len(columns_setting or [])
        if expected_count < 1:
            raise HarvestError("Table structure settings require expected_column_count.")
        horizontal_ys = [y + h // 2 for _, y, _, h in _line_segments(page_image, horizontal=True)]
        ranges_setting = settings.get("column_ranges")
        if ranges_setting:
            ranges, boundaries, confidence = _detect_column_ranges(page_image, detected_table.bbox, ranges_setting)
        else:
            boundaries, confidence = _detect_x_boundaries(page_image, detected_table.bbox, expected_count + 1, list(settings.get("fallback_x_boundaries", [])))
            ranges = list(zip(boundaries[:-1], boundaries[1:]))
        header = _header_bottom(detected_table.bbox, horizontal_ys)
        row_bounds = _detect_rows(page_image, detected_table.bbox, header, float(settings.get("row_merge_factor", .85)))
        rows = [Row(f"{detected_table.table_region_id}-row-{i:03d}", detected_table.table_region_id, i, (x0, top, x1, bottom)) for i, (top, bottom) in enumerate(row_bounds)]
        columns = [Column(f"{detected_table.table_region_id}-column-{i:03d}", detected_table.table_region_id, i, (left, header, right, y1)) for i, (left, right) in enumerate(ranges)]
        cells = [Cell(f"{detected_table.table_region_id}-cell-{row.row_index:03d}-{column.column_index:03d}", detected_table.table_region_id, row.row_index, column.column_index, (column.bbox[0], row.bbox[1], column.bbox[2], row.bbox[3])) for row in rows for column in columns]
        return rows, columns, cells
