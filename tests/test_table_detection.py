import cv2
import numpy as np

from harvest.modules.table_detection import LegacyOpenCVTableDetector
from harvest.types import DetectedTable


def test_legacy_detector_returns_geometry_only_table():
    image = np.zeros((240, 320), dtype=np.uint8)
    for y in (40, 100, 180):
        cv2.line(image, (25, y), (295, y), 255, 2)

    tables = LegacyOpenCVTableDetector().detect(image, {
        "document_id": "doc", "page_id": "doc-page-0001", "table_region_id": "doc-page-0001-table-000",
        "min_table_width_ratio": .65,
    })

    assert len(tables) == 1
    assert isinstance(tables[0], DetectedTable)
    assert tables[0].bbox[0] <= 25 and tables[0].bbox[2] >= 295
    assert isinstance(tables[0].confidence, float)
    assert tables[0].metadata["backend"] == "legacy_opencv"
    assert not hasattr(tables[0], "rows")
    assert not hasattr(tables[0], "semantic_name")
