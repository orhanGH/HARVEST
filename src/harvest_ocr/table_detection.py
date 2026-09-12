from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

from .utils import HarvestError, read_jsonl

BBox = tuple[float, float, float, float]
TABLE_LABELS = ("table", "table rotated")


@dataclass(slots=True)
class DetectionRecord:
    """Normalized table detection or annotation."""

    pdf_page: int
    bbox: BBox
    label: str = "table"
    score: float | None = None
    document_id: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.pdf_page < 1:
            raise HarvestError(f"pdf_page must be >= 1, got {self.pdf_page}")
        self.bbox = normalize_bbox(self.bbox)
        if self.score is not None:
            self.score = float(self.score)
        if self.image_width is not None and self.image_width <= 0:
            raise HarvestError(f"image_width must be > 0, got {self.image_width}")
        if self.image_height is not None and self.image_height <= 0:
            raise HarvestError(f"image_height must be > 0, got {self.image_height}")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["bbox"] = list(self.bbox)
        return payload


@dataclass(frozen=True, slots=True)
class DetectionMatch:
    prediction_index: int
    annotation_index: int
    iou: float
    prediction: DetectionRecord
    annotation: DetectionRecord

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["prediction"] = self.prediction.to_dict()
        payload["annotation"] = self.annotation.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class PageEvaluationSummary:
    pdf_page: int
    prediction_count: int
    annotation_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    mean_iou: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    mean_iou: float
    matched_pairs: int
    prediction_count: int
    annotation_count: int
    pages: list[PageEvaluationSummary]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["pages"] = [page.to_dict() for page in self.pages]
        return payload


def normalize_bbox(box: Sequence[float | int]) -> BBox:
    """Validate and normalize a bbox into ``(x0, y0, x1, y1)`` form."""

    if len(box) != 4:
        raise HarvestError(f"Bounding boxes require four values, got {len(box)}: {box!r}")
    try:
        x0, y0, x1, y1 = (float(value) for value in box)
    except (TypeError, ValueError) as exc:
        raise HarvestError(f"Bounding box values must be numeric: {box!r}") from exc
    if not all(math.isfinite(value) for value in (x0, y0, x1, y1)):
        raise HarvestError(f"Bounding box values must be finite: {box!r}")
    if x1 <= x0 or y1 <= y0:
        raise HarvestError(f"Bounding box must satisfy x1>x0 and y1>y0: {box!r}")
    return (x0, y0, x1, y1)


def clip_bbox(box: Sequence[float | int], width: int, height: int) -> BBox:
    """Clamp a bbox to image bounds."""

    if width <= 0 or height <= 0:
        raise HarvestError(f"Image bounds must be positive, got width={width}, height={height}")
    x0, y0, x1, y1 = normalize_bbox(box)
    clipped = (
        min(max(x0, 0.0), float(width)),
        min(max(y0, 0.0), float(height)),
        min(max(x1, 0.0), float(width)),
        min(max(y1, 0.0), float(height)),
    )
    if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
        raise HarvestError(
            f"Bounding box {box!r} falls outside image bounds width={width}, height={height}"
        )
    return clipped


def pad_bbox(
    box: Sequence[float | int],
    padding: float | int,
    *,
    width: int | None = None,
    height: int | None = None,
) -> BBox:
    """Expand a bbox by a uniform padding and optionally clamp it."""

    amount = float(padding)
    if amount < 0:
        raise HarvestError(f"padding must be >= 0, got {padding}")
    x0, y0, x1, y1 = normalize_bbox(box)
    padded = (x0 - amount, y0 - amount, x1 + amount, y1 + amount)
    if width is not None or height is not None:
        if width is None or height is None:
            raise HarvestError("width and height must be provided together when clipping padding")
        return clip_bbox(padded, width, height)
    return normalize_bbox(padded)


def bbox_area(box: Sequence[float | int]) -> float:
    x0, y0, x1, y1 = normalize_bbox(box)
    return (x1 - x0) * (y1 - y0)


def intersection_bbox(box_a: Sequence[float | int], box_b: Sequence[float | int]) -> BBox | None:
    x0a, y0a, x1a, y1a = normalize_bbox(box_a)
    x0b, y0b, x1b, y1b = normalize_bbox(box_b)
    left = max(x0a, x0b)
    top = max(y0a, y0b)
    right = min(x1a, x1b)
    bottom = min(y1a, y1b)
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def intersection_area(box_a: Sequence[float | int], box_b: Sequence[float | int]) -> float:
    intersection = intersection_bbox(box_a, box_b)
    if intersection is None:
        return 0.0
    return bbox_area(intersection)


def bbox_iou(box_a: Sequence[float | int], box_b: Sequence[float | int]) -> float:
    intersection = intersection_area(box_a, box_b)
    if intersection == 0:
        return 0.0
    union = bbox_area(box_a) + bbox_area(box_b) - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def overlap_ratio(box_a: Sequence[float | int], box_b: Sequence[float | int]) -> float:
    """Return overlap relative to the smaller box area."""

    intersection = intersection_area(box_a, box_b)
    if intersection == 0:
        return 0.0
    smaller = min(bbox_area(box_a), bbox_area(box_b))
    if smaller <= 0:
        return 0.0
    return intersection / smaller


def suppress_overlapping_detections(
    detections: Sequence[DetectionRecord],
    *,
    iou_threshold: float = 0.9,
    overlap_threshold: float = 0.8,
) -> list[DetectionRecord]:
    """Drop lower-ranked duplicate or heavily overlapping detections."""

    if not detections:
        return []
    ranked = sorted(
        enumerate(detections),
        key=lambda item: (
            item[1].pdf_page,
            -_sort_score(item[1].score),
            item[0],
            item[1].label,
        ),
    )
    kept: list[DetectionRecord] = []
    by_group: dict[tuple[int, str], list[DetectionRecord]] = {}
    for _, detection in ranked:
        group_key = (detection.pdf_page, detection.label)
        group = by_group.setdefault(group_key, [])
        duplicate = any(
            bbox_iou(detection.bbox, existing.bbox) >= iou_threshold
            or overlap_ratio(detection.bbox, existing.bbox) >= overlap_threshold
            for existing in group
        )
        if duplicate:
            continue
        group.append(detection)
        kept.append(detection)
    return kept


def match_detections(
    predictions: Sequence[DetectionRecord],
    annotations: Sequence[DetectionRecord],
    *,
    iou_threshold: float = 0.5,
) -> list[DetectionMatch]:
    """Greedily build one-to-one matches above the IoU threshold."""

    candidates: list[tuple[float, int, int]] = []
    for prediction_index, prediction in enumerate(predictions):
        for annotation_index, annotation in enumerate(annotations):
            if prediction.pdf_page != annotation.pdf_page:
                continue
            if _localization_label(prediction.label) != _localization_label(annotation.label):
                continue
            score = bbox_iou(prediction.bbox, annotation.bbox)
            if score >= iou_threshold:
                candidates.append((score, prediction_index, annotation_index))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    used_predictions: set[int] = set()
    used_annotations: set[int] = set()
    matches: list[DetectionMatch] = []
    for score, prediction_index, annotation_index in candidates:
        if prediction_index in used_predictions or annotation_index in used_annotations:
            continue
        used_predictions.add(prediction_index)
        used_annotations.add(annotation_index)
        matches.append(
            DetectionMatch(
                prediction_index=prediction_index,
                annotation_index=annotation_index,
                iou=score,
                prediction=predictions[prediction_index],
                annotation=annotations[annotation_index],
            )
        )
    matches.sort(key=lambda item: (item.prediction.pdf_page, item.prediction_index, item.annotation_index))
    return matches


def evaluate_detections(
    predictions: Sequence[DetectionRecord],
    annotations: Sequence[DetectionRecord],
    *,
    iou_threshold: float = 0.5,
) -> EvaluationSummary:
    """Evaluate predictions against annotations page by page."""

    matches = match_detections(predictions, annotations, iou_threshold=iou_threshold)
    page_numbers = sorted({record.pdf_page for record in predictions} | {record.pdf_page for record in annotations})
    matched_prediction_indexes = {match.prediction_index for match in matches}
    matched_annotation_indexes = {match.annotation_index for match in matches}
    page_summaries: list[PageEvaluationSummary] = []
    for page_number in page_numbers:
        page_prediction_indexes = [
            index for index, record in enumerate(predictions) if record.pdf_page == page_number
        ]
        page_annotation_indexes = [
            index for index, record in enumerate(annotations) if record.pdf_page == page_number
        ]
        page_matches = [match for match in matches if match.prediction.pdf_page == page_number]
        true_positives = len(page_matches)
        false_positives = len(
            [index for index in page_prediction_indexes if index not in matched_prediction_indexes]
        )
        false_negatives = len(
            [index for index in page_annotation_indexes if index not in matched_annotation_indexes]
        )
        precision = _safe_ratio(true_positives, true_positives + false_positives)
        recall = _safe_ratio(true_positives, true_positives + false_negatives)
        mean_iou = (
            sum(match.iou for match in page_matches) / len(page_matches) if page_matches else 0.0
        )
        page_summaries.append(
            PageEvaluationSummary(
                pdf_page=page_number,
                prediction_count=len(page_prediction_indexes),
                annotation_count=len(page_annotation_indexes),
                true_positives=true_positives,
                false_positives=false_positives,
                false_negatives=false_negatives,
                precision=precision,
                recall=recall,
                mean_iou=mean_iou,
            )
        )
    true_positives = len(matches)
    false_positives = len(predictions) - true_positives
    false_negatives = len(annotations) - true_positives
    precision = _safe_ratio(true_positives, len(predictions))
    recall = _safe_ratio(true_positives, len(annotations))
    mean_iou = sum(match.iou for match in matches) / len(matches) if matches else 0.0
    return EvaluationSummary(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        mean_iou=mean_iou,
        matched_pairs=len(matches),
        prediction_count=len(predictions),
        annotation_count=len(annotations),
        pages=page_summaries,
    )


def load_annotations(path: str | Path) -> list[DetectionRecord]:
    """Load page-oriented table annotations from JSON or JSONL."""

    annotation_path = Path(path)
    if not annotation_path.exists():
        raise HarvestError(f"Annotation file does not exist: {annotation_path}")
    if annotation_path.suffix.lower() == ".jsonl":
        rows = list(read_jsonl(annotation_path))
    else:
        with annotation_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            rows = payload.get("pages", [])
        elif isinstance(payload, list):
            rows = payload
        else:
            raise HarvestError(f"Unsupported annotation JSON payload in {annotation_path}")
    detections: list[DetectionRecord] = []
    for row in rows:
        detections.extend(_annotation_rows_to_detections(row, annotation_path))
    return detections


def serialize_bbox(box: Sequence[float | int], digits: int = 3) -> list[float]:
    """Round a bbox for stable JSON output."""

    return [round(value, digits) for value in normalize_bbox(box)]


def filter_labels(
    detections: Iterable[DetectionRecord],
    labels: Iterable[str] = TABLE_LABELS,
) -> list[DetectionRecord]:
    allowed = {label.casefold() for label in labels}
    return [detection for detection in detections if detection.label.casefold() in allowed]


def filter_scan_edge_artifacts(
    detections: Iterable[DetectionRecord],
    *,
    edge_margin_px: float = 5.0,
    edge_max_width_ratio: float = 0.05,
) -> list[DetectionRecord]:
    """Remove narrow detections hugging the left page boundary."""

    margin = float(edge_margin_px)
    max_width_ratio = float(edge_max_width_ratio)
    if margin < 0:
        raise HarvestError(f"edge_margin_px must be >= 0, got {edge_margin_px}")
    if max_width_ratio < 0 or max_width_ratio > 1:
        raise HarvestError(f"edge_max_width_ratio must be between 0 and 1, got {edge_max_width_ratio}")

    kept: list[DetectionRecord] = []
    for detection in detections:
        if detection.image_width is None or detection.image_width <= 0:
            kept.append(detection)
            continue
        x0, _, x1, _ = detection.bbox
        width_ratio = (x1 - x0) / float(detection.image_width)
        if x0 <= margin and width_ratio <= max_width_ratio:
            continue
        kept.append(detection)
    return kept


def merge_table_fragments(
    detections: Sequence[DetectionRecord],
    *,
    min_width_ratio: float = 0.50,
    min_horizontal_overlap: float = 0.80,
) -> list[DetectionRecord]:
    """Merge compatible wide, vertically overlapping fragments of one logical table."""

    width_ratio = float(min_width_ratio)
    horizontal_overlap = float(min_horizontal_overlap)
    if not 0.0 <= width_ratio <= 1.0:
        raise HarvestError(
            f"min_width_ratio must be between 0 and 1, got {min_width_ratio}"
        )
    if not 0.0 <= horizontal_overlap <= 1.0:
        raise HarvestError(
            "min_horizontal_overlap must be between 0 and 1, "
            f"got {min_horizontal_overlap}"
        )

    merged = list(detections)
    while True:
        merged_pair = False
        for left_index in range(len(merged)):
            for right_index in range(left_index + 1, len(merged)):
                left = merged[left_index]
                right = merged[right_index]
                if not _fragments_are_compatible(
                    left,
                    right,
                    min_width_ratio=width_ratio,
                    min_horizontal_overlap=horizontal_overlap,
                ):
                    continue
                merged[left_index] = _merge_fragment_pair(left, right)
                del merged[right_index]
                merged_pair = True
                break
            if merged_pair:
                break
        if not merged_pair:
            return merged


def _fragments_are_compatible(
    left: DetectionRecord,
    right: DetectionRecord,
    *,
    min_width_ratio: float,
    min_horizontal_overlap: float,
) -> bool:
    if left.pdf_page != right.pdf_page:
        return False
    if _localization_label(left.label) != _localization_label(right.label):
        return False
    if left.document_id and right.document_id and left.document_id != right.document_id:
        return False
    if left.image_width is None or right.image_width is None:
        return False

    left_width = left.bbox[2] - left.bbox[0]
    right_width = right.bbox[2] - right.bbox[0]
    if left_width / float(left.image_width) < min_width_ratio:
        return False
    if right_width / float(right.image_width) < min_width_ratio:
        return False

    x_overlap = max(
        0.0,
        min(left.bbox[2], right.bbox[2]) - max(left.bbox[0], right.bbox[0]),
    )
    smaller_width = min(left_width, right_width)
    if smaller_width <= 0 or x_overlap / smaller_width < min_horizontal_overlap:
        return False

    y_overlap = min(left.bbox[3], right.bbox[3]) - max(left.bbox[1], right.bbox[1])
    return y_overlap > 0


def _merge_fragment_pair(left: DetectionRecord, right: DetectionRecord) -> DetectionRecord:
    left_score = _sort_score(left.score)
    right_score = _sort_score(right.score)
    primary = left if left_score >= right_score else right
    score = None if left.score is None and right.score is None else max(left_score, right_score)

    metadata = dict(primary.metadata)
    components: list[dict[str, Any]] = []
    for detection in (left, right):
        existing = detection.metadata.get("fragment_merge_components")
        if isinstance(existing, list):
            components.extend(existing)
            continue
        component_metadata = {
            key: value
            for key, value in detection.metadata.items()
            if key not in {"fragment_merged", "fragment_merge_components"}
        }
        components.append(
            {
                "bbox": serialize_bbox(detection.bbox),
                "label": detection.label,
                "score": detection.score,
                "metadata": component_metadata,
            }
        )

    metadata["fragment_merged"] = True
    metadata["fragment_merge_components"] = components

    return DetectionRecord(
        pdf_page=primary.pdf_page,
        bbox=(
            min(left.bbox[0], right.bbox[0]),
            min(left.bbox[1], right.bbox[1]),
            max(left.bbox[2], right.bbox[2]),
            max(left.bbox[3], right.bbox[3]),
        ),
        label=primary.label,
        score=score,
        document_id=primary.document_id or left.document_id or right.document_id,
        image_width=primary.image_width or left.image_width or right.image_width,
        image_height=primary.image_height or left.image_height or right.image_height,
        source=primary.source or left.source or right.source,
        metadata=metadata,
    )


def _annotation_rows_to_detections(row: Any, source_path: Path) -> list[DetectionRecord]:
    if not isinstance(row, dict):
        raise HarvestError(f"Annotation rows in {source_path} must be JSON objects")
    if "annotations" in row:
        pdf_page = _int_field(row, "pdf_page", source_path)
        document_id = _optional_str(row.get("document_id"))
        image_width = _optional_int(row.get("image_width"))
        image_height = _optional_int(row.get("image_height"))
        annotations = row.get("annotations")
        if not isinstance(annotations, list):
            raise HarvestError(f"'annotations' must be a list in {source_path}")
        detections: list[DetectionRecord] = []
        for annotation in annotations:
            if not isinstance(annotation, dict):
                raise HarvestError(f"Each annotation must be an object in {source_path}")
            detections.append(
                DetectionRecord(
                    pdf_page=pdf_page,
                    bbox=annotation["bbox"],
                    label=str(annotation.get("label", "table")),
                    score=None,
                    document_id=document_id,
                    image_width=image_width,
                    image_height=image_height,
                    source=str(source_path),
                    metadata=_clean_metadata(annotation, {"bbox", "label"}),
                )
            )
        return detections
    if "bbox" in row:
        return [
            DetectionRecord(
                pdf_page=_int_field(row, "pdf_page", source_path),
                bbox=row["bbox"],
                label=str(row.get("label", "table")),
                score=None,
                document_id=_optional_str(row.get("document_id")),
                image_width=_optional_int(row.get("image_width")),
                image_height=_optional_int(row.get("image_height")),
                source=str(source_path),
                metadata=_clean_metadata(
                    row,
                    {"pdf_page", "bbox", "label", "document_id", "image_width", "image_height"},
                ),
            )
        ]
    raise HarvestError(
        f"Annotation rows in {source_path} must contain either 'annotations' or 'bbox'"
    )


def _int_field(row: dict[str, Any], name: str, source_path: Path) -> int:
    try:
        value = int(row[name])
    except KeyError as exc:
        raise HarvestError(f"Missing required annotation field {name!r} in {source_path}") from exc
    except (TypeError, ValueError) as exc:
        raise HarvestError(f"Annotation field {name!r} must be an integer in {source_path}") from exc
    return value


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _clean_metadata(value: dict[str, Any], excluded: set[str]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in excluded}


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _sort_score(score: float | None) -> float:
    if score is None:
        return 0.0
    return float(score)


def _localization_label(label: str) -> str:
    normalized = label.strip().casefold()
    if normalized in {"table", "table rotated"}:
        return "table"
    return normalized


__all__ = [
    "BBox",
    "DetectionMatch",
    "DetectionRecord",
    "EvaluationSummary",
    "PageEvaluationSummary",
    "TABLE_LABELS",
    "bbox_area",
    "bbox_iou",
    "clip_bbox",
    "evaluate_detections",
    "filter_scan_edge_artifacts",
    "filter_labels",
    "intersection_area",
    "intersection_bbox",
    "load_annotations",
    "match_detections",
    "merge_table_fragments",
    "normalize_bbox",
    "overlap_ratio",
    "pad_bbox",
    "serialize_bbox",
    "suppress_overlapping_detections",
]
