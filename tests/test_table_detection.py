import math

import pytest

from harvest_ocr.table_detection import (
    DetectionRecord,
    bbox_area,
    bbox_iou,
    clip_bbox,
    evaluate_detections,
    filter_scan_edge_artifacts,
    load_annotations,
    match_detections,
    merge_table_fragments,
    normalize_bbox,
    overlap_ratio,
    pad_bbox,
    suppress_overlapping_detections,
)
from harvest_ocr.utils import HarvestError, write_json


def test_normalize_bbox_accepts_numeric_sequences():
    assert normalize_bbox([1, 2.5, 10, 20]) == (1.0, 2.5, 10.0, 20.0)


@pytest.mark.parametrize("box", [(), (1, 2, 3), (3, 2, 1, 4), (1, 5, 2, 5)])
def test_normalize_bbox_rejects_invalid_boxes(box):
    with pytest.raises(HarvestError):
        normalize_bbox(box)


def test_clip_bbox_clamps_to_image_bounds():
    assert clip_bbox((-5, 10, 105, 210), width=100, height=200) == (0.0, 10.0, 100.0, 200.0)


def test_pad_bbox_expands_and_clamps():
    assert pad_bbox((10, 15, 40, 45), 8, width=42, height=50) == (2.0, 7.0, 42.0, 50.0)


def test_bbox_iou_and_overlap_ratio():
    first = (0, 0, 10, 10)
    second = (5, 5, 15, 15)
    assert bbox_area(first) == 100.0
    assert math.isclose(bbox_iou(first, second), 25 / 175)
    assert math.isclose(overlap_ratio(first, second), 0.25)


def test_suppress_overlapping_detections_keeps_highest_score():
    detections = [
        DetectionRecord(pdf_page=20, bbox=(10, 10, 100, 100), label="table", score=0.95),
        DetectionRecord(pdf_page=20, bbox=(12, 12, 98, 98), label="table", score=0.60),
        DetectionRecord(pdf_page=20, bbox=(130, 20, 200, 80), label="table", score=0.70),
        DetectionRecord(pdf_page=20, bbox=(10, 10, 100, 100), label="table rotated", score=0.90),
    ]
    kept = suppress_overlapping_detections(detections, iou_threshold=0.9, overlap_threshold=0.8)
    assert [record.label for record in kept] == ["table", "table rotated", "table"]
    assert [round(record.score or 0.0, 2) for record in kept] == [0.95, 0.9, 0.7]


def test_filter_scan_edge_artifacts_removes_narrow_left_edge_strip():
    detections = [
        DetectionRecord(
            pdf_page=25,
            bbox=(2, 50, 40, 500),
            label="table",
            score=0.8,
            image_width=1000,
            image_height=1400,
        )
    ]
    kept = filter_scan_edge_artifacts(detections)
    assert kept == []


def test_filter_scan_edge_artifacts_keeps_narrow_box_away_from_left_edge():
    detections = [
        DetectionRecord(
            pdf_page=27,
            bbox=(20, 50, 58, 500),
            label="table",
            score=0.8,
            image_width=1000,
            image_height=1400,
        )
    ]
    kept = filter_scan_edge_artifacts(detections)
    assert len(kept) == 1
    assert kept[0].bbox == (20.0, 50.0, 58.0, 500.0)


def test_filter_scan_edge_artifacts_keeps_wide_table_touching_left_edge():
    detections = [
        DetectionRecord(
            pdf_page=29,
            bbox=(1, 50, 240, 500),
            label="table",
            score=0.8,
            image_width=1000,
            image_height=1400,
        )
    ]
    kept = filter_scan_edge_artifacts(detections)
    assert len(kept) == 1
    assert kept[0].bbox == (1.0, 50.0, 240.0, 500.0)


def test_filter_scan_edge_artifacts_removes_box_at_width_ratio_threshold():
    detections = [
        DetectionRecord(
            pdf_page=29,
            bbox=(3, 50, 53, 500),
            label="table",
            score=0.8,
            image_width=1000,
            image_height=1400,
        )
    ]
    kept = filter_scan_edge_artifacts(detections, edge_max_width_ratio=0.05)
    assert kept == []


def test_filter_scan_edge_artifacts_keeps_normal_table_detection():
    detections = [
        DetectionRecord(
            pdf_page=31,
            bbox=(120, 80, 780, 950),
            label="table",
            score=0.9,
            image_width=1000,
            image_height=1400,
        )
    ]
    kept = filter_scan_edge_artifacts(detections)
    assert len(kept) == 1
    assert kept[0].bbox == (120.0, 80.0, 780.0, 950.0)


def test_filter_scan_edge_artifacts_rejects_negative_edge_margin():
    detections = [
        DetectionRecord(
            pdf_page=31,
            bbox=(120, 80, 780, 950),
            label="table",
            score=0.9,
            image_width=1000,
            image_height=1400,
        )
    ]
    with pytest.raises(HarvestError):
        filter_scan_edge_artifacts(detections, edge_margin_px=-1)


@pytest.mark.parametrize("ratio", [-0.1, 1.1])
def test_filter_scan_edge_artifacts_rejects_out_of_range_width_ratio(ratio):
    detections = [
        DetectionRecord(
            pdf_page=31,
            bbox=(120, 80, 780, 950),
            label="table",
            score=0.9,
            image_width=1000,
            image_height=1400,
        )
    ]
    with pytest.raises(HarvestError):
        filter_scan_edge_artifacts(detections, edge_max_width_ratio=ratio)


def _fragment(
    bbox,
    *,
    page=30,
    label="table",
    score=0.5,
    image_width=1530,
    image_height=1786,
):
    return DetectionRecord(
        pdf_page=page,
        bbox=bbox,
        label=label,
        score=score,
        document_id="sample",
        image_width=image_width,
        image_height=image_height,
        source="model",
    )


def test_merge_table_fragments_merges_page30_style_fragments():
    detections = [
        _fragment((257.331, 518.244, 1360.872, 1114.935), score=0.2355),
        _fragment((245.249, 995.461, 1353.302, 1342.566), score=0.1491),
    ]
    merged = merge_table_fragments(detections)
    assert len(merged) == 1
    assert merged[0].bbox == (245.249, 518.244, 1360.872, 1342.566)
    assert merged[0].score == pytest.approx(0.2355)
    assert merged[0].metadata["fragment_merged"] is True
    assert len(merged[0].metadata["fragment_merge_components"]) == 2


def test_merge_table_fragments_merges_page36_style_fragments():
    detections = [
        _fragment((262.029, 667.773, 1380.528, 876.129), page=36, score=0.1630),
        _fragment((276.298, 398.471, 1380.163, 708.603), page=36, score=0.1160),
    ]
    merged = merge_table_fragments(detections)
    assert len(merged) == 1
    assert merged[0].bbox == (262.029, 398.471, 1380.528, 876.129)


def test_merge_table_fragments_keeps_vertically_separated_boxes():
    detections = [
        _fragment((100, 100, 1300, 400)),
        _fragment((110, 450, 1310, 800)),
    ]
    assert len(merge_table_fragments(detections)) == 2


def test_merge_table_fragments_keeps_horizontally_misaligned_boxes():
    detections = [
        _fragment((0, 100, 800, 500)),
        _fragment((700, 400, 1500, 800)),
    ]
    assert len(merge_table_fragments(detections)) == 2


def test_merge_table_fragments_keeps_narrow_boxes():
    detections = [
        _fragment((100, 100, 700, 500)),
        _fragment((110, 400, 710, 800)),
    ]
    assert len(merge_table_fragments(detections)) == 2


def test_merge_table_fragments_normalizes_table_rotated_label():
    detections = [
        _fragment((100, 100, 1300, 500), label="table", score=0.4),
        _fragment((110, 400, 1310, 800), label="table rotated", score=0.8),
    ]
    merged = merge_table_fragments(detections)
    assert len(merged) == 1
    assert merged[0].label == "table rotated"
    assert merged[0].score == pytest.approx(0.8)


def test_merge_table_fragments_merges_iteratively():
    detections = [
        _fragment((100, 100, 1300, 350), score=0.7),
        _fragment((105, 300, 1305, 550), score=0.6),
        _fragment((110, 500, 1310, 750), score=0.5),
    ]
    merged = merge_table_fragments(detections)
    assert len(merged) == 1
    assert merged[0].bbox == (100.0, 100.0, 1310.0, 750.0)
    assert len(merged[0].metadata["fragment_merge_components"]) == 3


def test_match_detections_is_one_to_one():
    predictions = [
        DetectionRecord(pdf_page=20, bbox=(10, 10, 50, 50), label="table", score=0.9),
        DetectionRecord(pdf_page=20, bbox=(12, 12, 49, 49), label="table", score=0.8),
        DetectionRecord(pdf_page=21, bbox=(0, 0, 10, 10), label="table", score=0.7),
    ]
    annotations = [
        DetectionRecord(pdf_page=20, bbox=(11, 11, 51, 51), label="table"),
        DetectionRecord(pdf_page=21, bbox=(0, 0, 10, 10), label="table"),
    ]
    matches = match_detections(predictions, annotations, iou_threshold=0.5)
    assert len(matches) == 2
    assert matches[0].prediction_index == 0
    assert matches[0].annotation_index == 0
    assert matches[1].prediction_index == 2
    assert matches[1].annotation_index == 1


def test_match_detections_treats_table_rotated_as_table_for_localization():
    predictions = [
        DetectionRecord(pdf_page=20, bbox=(10, 10, 50, 50), label="table rotated", score=0.9),
    ]
    annotations = [
        DetectionRecord(pdf_page=20, bbox=(10, 10, 50, 50), label="table"),
    ]
    matches = match_detections(predictions, annotations, iou_threshold=0.5)
    assert len(matches) == 1
    assert matches[0].prediction.label == "table rotated"
    assert matches[0].to_dict()["prediction"]["label"] == "table rotated"


def test_evaluate_detections_handles_empty_inputs():
    summary = evaluate_detections([], [], iou_threshold=0.5)
    assert summary.true_positives == 0
    assert summary.false_positives == 0
    assert summary.false_negatives == 0
    assert summary.precision == 0.0
    assert summary.recall == 0.0
    assert summary.mean_iou == 0.0
    assert summary.pages == []


def test_evaluate_detections_reports_per_page_totals():
    predictions = [
        DetectionRecord(pdf_page=20, bbox=(10, 10, 50, 50), label="table", score=0.9),
        DetectionRecord(pdf_page=20, bbox=(60, 60, 90, 90), label="table", score=0.7),
        DetectionRecord(pdf_page=21, bbox=(0, 0, 20, 20), label="table rotated", score=0.8),
    ]
    annotations = [
        DetectionRecord(pdf_page=20, bbox=(11, 10, 51, 50), label="table"),
        DetectionRecord(pdf_page=21, bbox=(0, 0, 20, 20), label="table rotated"),
        DetectionRecord(pdf_page=21, bbox=(50, 50, 70, 70), label="table"),
    ]
    summary = evaluate_detections(predictions, annotations, iou_threshold=0.5)
    assert summary.true_positives == 2
    assert summary.false_positives == 1
    assert summary.false_negatives == 1
    assert math.isclose(summary.precision, 2 / 3)
    assert math.isclose(summary.recall, 2 / 3)
    assert len(summary.pages) == 2
    assert summary.pages[0].pdf_page == 20
    assert summary.pages[0].true_positives == 1
    assert summary.pages[0].false_positives == 1
    assert summary.pages[1].pdf_page == 21
    assert summary.pages[1].false_negatives == 1


def test_evaluate_detections_treats_table_rotated_as_table_for_localization():
    predictions = [
        DetectionRecord(pdf_page=20, bbox=(10, 10, 50, 50), label="table rotated", score=0.9),
    ]
    annotations = [
        DetectionRecord(pdf_page=20, bbox=(10, 10, 50, 50), label="table"),
    ]
    summary = evaluate_detections(predictions, annotations, iou_threshold=0.5)
    assert summary.true_positives == 1
    assert summary.false_positives == 0
    assert summary.false_negatives == 0
    assert summary.pages[0].true_positives == 1


def test_load_annotations_supports_json_page_records(tmp_path):
    annotation_path = tmp_path / "annotations.json"
    write_json(
        annotation_path,
        {
            "pages": [
                {
                    "document_id": "sample-doc",
                    "pdf_page": 20,
                    "image_width": 1000,
                    "image_height": 1500,
                    "annotations": [
                        {"label": "table", "bbox": [10, 20, 30, 40], "annotator": "tester"},
                        {"label": "table rotated", "bbox": [50, 60, 90, 120]},
                    ],
                }
            ]
        },
    )
    annotations = load_annotations(annotation_path)
    assert len(annotations) == 2
    assert annotations[0].document_id == "sample-doc"
    assert annotations[0].metadata == {"annotator": "tester"}
    assert annotations[1].label == "table rotated"
