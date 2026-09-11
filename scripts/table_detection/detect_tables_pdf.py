#!/usr/bin/env python3
"""Run the Hugging Face Table Transformer detector on PDF pages."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any

from harvest_ocr.table_detection import (
    TABLE_LABELS,
    DetectionRecord,
    clip_bbox,
    evaluate_detections,
    filter_scan_edge_artifacts,
    filter_labels,
    load_annotations,
    pad_bbox,
    serialize_bbox,
    suppress_overlapping_detections,
)
from harvest_ocr.utils import HarvestError, parse_page_range, safe_stem, write_json, write_jsonl

DEFAULT_MODEL = "microsoft/table-transformer-detection"
DEFAULT_PAGES = "20-45"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, help="Source PDF path")
    parser.add_argument(
        "--output-dir",
        help="Run output directory (default: runs/table_detection/<pdf-stem>/<timestamp>)",
    )
    parser.add_argument("--pages", default=DEFAULT_PAGES, help=f"One-based page range (default: {DEFAULT_PAGES})")
    parser.add_argument("--dpi", type=int, default=180, help="Page render DPI")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Hugging Face detector model")
    parser.add_argument("--threshold", type=float, default=0.50, help="Score threshold")
    parser.add_argument(
        "--device",
        default="auto",
        help="Inference device: auto, cpu, cuda, cuda:0, mps, ...",
    )
    parser.add_argument(
        "--bbox-padding",
        type=float,
        default=8.0,
        help="Uniform pixel padding applied to crop_bbox after detection",
    )
    parser.add_argument(
        "--duplicate-iou-threshold",
        type=float,
        default=0.9,
        help="IoU threshold for duplicate suppression",
    )
    parser.add_argument(
        "--duplicate-overlap-threshold",
        type=float,
        default=0.8,
        help="Smaller-box overlap threshold for duplicate suppression",
    )
    parser.add_argument(
        "--annotations",
        help="Optional JSON/JSONL annotation file for evaluation",
    )
    parser.add_argument(
        "--match-iou-threshold",
        type=float,
        default=0.5,
        help="IoU threshold for prediction/annotation matching",
    )
    edge_filter_group = parser.add_mutually_exclusive_group()
    edge_filter_group.add_argument(
        "--edge-artifact-filter",
        dest="edge_artifact_filter",
        action="store_true",
        help="Filter narrow detections touching the left page boundary",
    )
    edge_filter_group.add_argument(
        "--no-edge-artifact-filter",
        dest="edge_artifact_filter",
        action="store_false",
        help="Disable left-edge artifact filtering",
    )
    parser.set_defaults(edge_artifact_filter=True)
    parser.add_argument(
        "--edge-margin-px",
        type=float,
        default=5.0,
        help="Left-page margin in pixels used for edge artifact filtering",
    )
    parser.add_argument(
        "--edge-max-width-ratio",
        type=float,
        default=0.05,
        help="Maximum bbox_width/image_width ratio to treat as an edge artifact",
    )
    parser.add_argument(
        "--save-page-renders",
        action="store_true",
        help="Persist rendered page PNGs under the run directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_detection(args)
    except HarvestError as exc:
        print(f"HARVEST error: {exc}")
        return 2
    print(json.dumps(result, indent=2))
    return 0


def run_detection(args: argparse.Namespace) -> dict[str, Any]:
    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        raise HarvestError(f"Input PDF does not exist: {pdf_path}")
    output_dir = _resolve_output_dir(pdf_path, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fitz = _import_pymupdf()
    processor, model, torch, resolved_device = _load_detector(args.model, args.device)
    start_time = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()

    detections: list[DetectionRecord] = []
    pages_payload: list[dict[str, Any]] = []
    raw_prediction_count = 0
    edge_filter_input_count = 0
    edge_filter_removed_count = 0

    with fitz.open(pdf_path) as document:
        pages = parse_page_range(args.pages, document.page_count)
        if not pages:
            raise HarvestError("No PDF pages were selected")
        render_dir = output_dir / "pages"
        for pdf_page in pages:
            image = render_pdf_page(document, pdf_page, args.dpi, fitz)
            page_path = None
            if args.save_page_renders:
                render_dir.mkdir(parents=True, exist_ok=True)
                page_path = render_dir / f"page-{pdf_page:04d}.png"
                image.save(page_path)
            page_predictions = detect_tables(
                image=image,
                pdf_page=pdf_page,
                model_name=args.model,
                threshold=args.threshold,
                document_id=safe_stem(pdf_path.stem),
                processor=processor,
                model=model,
                torch_module=torch,
                device=resolved_device,
            )
            raw_prediction_count += len(page_predictions)
            page_predictions = filter_labels(page_predictions, TABLE_LABELS)
            edge_filter_input_count += len(page_predictions)
            if args.edge_artifact_filter:
                filtered_predictions = filter_scan_edge_artifacts(
                    page_predictions,
                    edge_margin_px=args.edge_margin_px,
                    edge_max_width_ratio=args.edge_max_width_ratio,
                )
                edge_filter_removed_count += len(page_predictions) - len(filtered_predictions)
                page_predictions = filtered_predictions
            page_predictions = suppress_overlapping_detections(
                page_predictions,
                iou_threshold=args.duplicate_iou_threshold,
                overlap_threshold=args.duplicate_overlap_threshold,
            )
            pages_payload.append(
                _page_payload(
                    pdf_page=pdf_page,
                    pdf_path=pdf_path,
                    image=image,
                    page_path=page_path,
                    detections=page_predictions,
                    padding=args.bbox_padding,
                )
            )
            detections.extend(page_predictions)

    detection_rows = _detection_rows(detections, bbox_padding=args.bbox_padding)
    write_jsonl(output_dir / "pages.jsonl", pages_payload)
    write_jsonl(output_dir / "detections.jsonl", detection_rows)

    evaluation_payload = None
    if args.annotations:
        annotations = filter_labels(load_annotations(args.annotations), TABLE_LABELS)
        evaluation_payload = evaluate_detections(
            detections,
            annotations,
            iou_threshold=args.match_iou_threshold,
        ).to_dict()
        write_json(output_dir / "evaluation.json", evaluation_payload)

    elapsed = time.perf_counter() - start_time
    label_counts = Counter(detection.label for detection in detections)
    summary = {
        "pdf_path": str(pdf_path),
        "document_id": safe_stem(pdf_path.stem),
        "output_dir": str(output_dir),
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(elapsed, 3),
        "model_name": args.model,
        "device": resolved_device,
        "pages": pages,
        "page_count": len(pages),
        "pages_with_predictions": sum(1 for page in pages_payload if page["detection_count"] > 0),
        "detections_before_filtering": raw_prediction_count,
        "detections_before_edge_filtering": edge_filter_input_count,
        "detections_removed_by_edge_filtering": edge_filter_removed_count,
        "detections_after_filtering": len(detection_rows),
        "label_counts": dict(sorted(label_counts.items())),
        "threshold": args.threshold,
        "dpi": args.dpi,
        "bbox_padding": args.bbox_padding,
        "kept_labels": list(TABLE_LABELS),
        "edge_artifact_filter": {
            "enabled": bool(args.edge_artifact_filter),
            "edge_margin_px": args.edge_margin_px,
            "edge_max_width_ratio": args.edge_max_width_ratio,
        },
        "artifacts": {
            "pages_jsonl": str(output_dir / "pages.jsonl"),
            "detections_jsonl": str(output_dir / "detections.jsonl"),
            "evaluation_json": str(output_dir / "evaluation.json") if evaluation_payload else None,
        },
        "evaluation": evaluation_payload,
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def render_pdf_page(document, pdf_page: int, dpi: int, fitz_module):
    if dpi <= 0:
        raise HarvestError(f"dpi must be > 0, got {dpi}")
    page = document.load_page(pdf_page - 1)
    scale = dpi / 72.0
    pixmap = page.get_pixmap(matrix=fitz_module.Matrix(scale, scale), alpha=False)
    try:
        from PIL import Image
    except ImportError as exc:
        raise HarvestError("Pillow is required. Install with: pip install 'Pillow>=10.0'") from exc
    return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)


def detect_tables(
    *,
    image,
    pdf_page: int,
    model_name: str,
    threshold: float,
    document_id: str,
    processor,
    model,
    torch_module,
    device: str,
) -> list[DetectionRecord]:
    inputs = processor(images=image, return_tensors="pt")
    inputs = {name: value.to(device) for name, value in inputs.items()}
    with torch_module.no_grad():
        outputs = model(**inputs)
    target_sizes = torch_module.tensor([(image.height, image.width)], device=device)
    processed = processor.post_process_object_detection(
        outputs,
        threshold=threshold,
        target_sizes=target_sizes,
    )[0]
    records: list[DetectionRecord] = []
    labels = processed["labels"].tolist()
    scores = processed["scores"].tolist()
    boxes = processed["boxes"].tolist()
    for index, (label_id, score, box) in enumerate(zip(labels, scores, boxes), 1):
        label = str(model.config.id2label[int(label_id)])
        normalized = clip_bbox(box, image.width, image.height)
        records.append(
            DetectionRecord(
                pdf_page=pdf_page,
                bbox=normalized,
                label=label,
                score=float(score),
                document_id=document_id,
                image_width=image.width,
                image_height=image.height,
                source=model_name,
                metadata={"raw_detection_index": index},
            )
        )
    return records


def _detection_rows(
    detections: list[DetectionRecord],
    *,
    bbox_padding: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    per_page_index: dict[int, int] = {}
    ordered = sorted(
        detections,
        key=lambda item: (item.pdf_page, -float(item.score or 0.0), item.bbox),
    )
    for detection in ordered:
        per_page_index[detection.pdf_page] = per_page_index.get(detection.pdf_page, 0) + 1
        page_index = per_page_index[detection.pdf_page]
        crop_bbox = _crop_bbox(detection, bbox_padding)
        rows.append(
            {
                "detection_id": f"{detection.document_id or 'document'}-p{detection.pdf_page:04d}-d{page_index:03d}",
                "document_id": detection.document_id,
                "pdf_page": detection.pdf_page,
                "label": detection.label,
                "score": round(float(detection.score or 0.0), 6),
                "bbox": serialize_bbox(detection.bbox),
                "crop_bbox": serialize_bbox(crop_bbox),
                "image_width": detection.image_width,
                "image_height": detection.image_height,
                "source": detection.source,
                "metadata": dict(detection.metadata),
            }
        )
    return rows


def _page_payload(
    *,
    pdf_page: int,
    pdf_path: Path,
    image,
    page_path: Path | None,
    detections: list[DetectionRecord],
    padding: float,
) -> dict[str, Any]:
    rows = _detection_rows(detections, bbox_padding=padding)
    return {
        "document_id": safe_stem(pdf_path.stem),
        "pdf_path": str(pdf_path),
        "pdf_page": pdf_page,
        "image_width": image.width,
        "image_height": image.height,
        "page_image": str(page_path) if page_path else None,
        "detection_count": len(rows),
        "detections": rows,
    }


def _crop_bbox(detection: DetectionRecord, padding: float) -> tuple[float, float, float, float]:
    if detection.image_width is None or detection.image_height is None:
        return pad_bbox(detection.bbox, padding)
    return pad_bbox(
        detection.bbox,
        padding,
        width=detection.image_width,
        height=detection.image_height,
    )


def _resolve_output_dir(pdf_path: Path, output_dir: str | None) -> Path:
    if output_dir:
        return Path(output_dir).resolve()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (Path("runs") / "table_detection" / safe_stem(pdf_path.stem) / timestamp).resolve()


def _import_pymupdf():
    try:
        import fitz
    except ImportError as exc:
        raise HarvestError("PyMuPDF is required. Install with: pip install 'PyMuPDF>=1.24'") from exc
    return fitz


def _load_detector(model_name: str, device_name: str):
    try:
        import torch
    except ImportError as exc:
        raise HarvestError(
            "PyTorch is required for table detection. Install the correct torch build for your "
            "platform first, then install Transformers."
        ) from exc
    try:
        from transformers import AutoImageProcessor, TableTransformerForObjectDetection
    except ImportError as exc:
        raise HarvestError(
            "Transformers is required for table detection. Install with: "
            "pip install 'transformers>=4.39'"
        ) from exc

    resolved_device = _resolve_device(torch, device_name)
    processor = AutoImageProcessor.from_pretrained(model_name)
    model = TableTransformerForObjectDetection.from_pretrained(model_name)
    model.to(resolved_device)
    model.eval()
    return processor, model, torch, resolved_device


def _resolve_device(torch_module, device_name: str) -> str:
    if device_name != "auto":
        return device_name
    if torch_module.cuda.is_available():
        return "cuda"
    if hasattr(torch_module.backends, "mps") and torch_module.backends.mps.is_available():
        return "mps"
    return "cpu"


if __name__ == "__main__":
    raise SystemExit(main())
