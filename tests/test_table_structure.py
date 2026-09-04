import cv2
import numpy as np

from harvest.modules.table_structure import LegacyRulesTableStructureRecognizer
from harvest.types import DetectedTable


def test_structure_extracts_provenance_geometry_only():
    image = np.zeros((200, 300), dtype=np.uint8)
    for x in (20, 110, 200, 280):
        cv2.line(image, (x, 20), (x, 180), 255, 2)
    for y in (20, 60, 100, 140, 180):
        cv2.line(image, (20, y), (280, y), 255, 2)
    for y in (80, 120, 160):
        for x in (35, 125, 215):
            cv2.putText(image, "123456", (x, y), cv2.FONT_HERSHEY_SIMPLEX, .6, 255, 2)
    table = DetectedTable("doc-page-0001-table-000", "doc", "doc-page-0001", (20, 20, 280, 180), 1.0)

    rows, columns, cells = LegacyRulesTableStructureRecognizer().extract(
        table, image, {"expected_column_count": 3, "row_merge_factor": .85}
    )

    assert rows and len(columns) == 3 and cells
    assert all(cell.table_region_id == table.table_region_id for cell in cells)
    assert all(not hasattr(cell, "text") for cell in cells)
    assert all(column.semantic_name is None for column in columns)
    assert cells[0].to_dict()["cell_id"] == cells[0].cell_id
    assert all(cell.row_index < len(rows) and cell.column_index < len(columns) for cell in cells)
