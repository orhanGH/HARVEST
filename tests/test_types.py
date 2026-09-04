from harvest.types import (
    BoundingBox,
    Cell,
    LogicalTable,
    OCRCharacter,
    OCRResult,
)


def test_bounding_box_is_frozen_and_serializes_to_tuple():
    box = BoundingBox(1, 2, 3, 4)

    assert box.to_tuple() == (1, 2, 3, 4)
    try:
        box.x0 = 0
    except AttributeError:
        pass
    else:
        raise AssertionError("BoundingBox must be frozen")


def test_cell_is_geometry_only_and_serializes():
    cell = Cell("cell-1", "region-1", "row-1", "column-1", BoundingBox(1, 2, 3, 4))

    assert cell.to_dict() == {
        "cell_id": "cell-1",
        "table_region_id": "region-1",
        "row_id": "row-1",
        "column_id": "column-1",
        "bbox": (1, 2, 3, 4),
    }
    assert "text" not in cell.to_dict()


def test_ocr_result_preserves_raw_text_and_symbols():
    result = OCRResult(
        "cell-1",
        "effocr",
        "A-*",
        [OCRCharacter("A"), OCRCharacter("-"), OCRCharacter("*")],
    )

    assert result.to_dict()["raw_text"] == "A-*"
    assert [character["symbol"] for character in result.to_dict()["characters"]] == [
        "A",
        "-",
        "*",
    ]


def test_logical_table_groups_multiple_regions_and_serializes():
    table = LogicalTable("logical-1", "document-1", ["region-1", "region-2"])

    assert table.to_dict() == {
        "logical_table_id": "logical-1",
        "document_id": "document-1",
        "table_region_ids": ["region-1", "region-2"],
        "metadata": {},
    }
