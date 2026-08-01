from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import fitz
import numpy as np

from backend.app.core.config import settings


def _to_list(value: Any) -> list:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        return value.tolist()
    return list(value)


@lru_cache(maxsize=1)
def get_ocr_engine():
    # PaddleOCR is deliberately imported lazily: normal PyMuPDF extraction does
    # not need to initialize the OCR runtime or download OCR model weights.
    from paddleocr import PaddleOCR

    return PaddleOCR(
        lang=settings.paddle_ocr_language,
        ocr_version=settings.paddle_ocr_version,
        device=settings.paddle_ocr_device,
        enable_mkldnn=settings.ocr_enable_mkldnn,
        text_rec_score_thresh=settings.ocr_text_score_threshold,
        use_doc_orientation_classify=settings.ocr_use_doc_orientation,
        use_doc_unwarping=False,
        use_textline_orientation=settings.ocr_use_textline_orientation,
    )


def _render_pdf_pages(
    pdf_path: Path,
    page_numbers: set[int] | None = None,
) -> Iterable[tuple[int, np.ndarray]]:
    max_side = max(1, settings.ocr_max_render_side)
    max_pixels = max(1, settings.ocr_max_render_pixels)

    with fitz.open(pdf_path) as document:
        render_dpi = settings.ocr_render_dpi
        if len(document) > settings.ocr_large_document_page_threshold:
            render_dpi = min(render_dpi, settings.ocr_large_document_dpi)
        base_scale = render_dpi / 72
        for page_number, page in enumerate(document, start=1):
            if page_numbers is not None and page_number not in page_numbers:
                continue
            page_width = max(float(page.rect.width), 1.0)
            page_height = max(float(page.rect.height), 1.0)
            scale = min(
                base_scale,
                max_side / max(page_width, page_height),
                (max_pixels / (page_width * page_height)) ** 0.5,
            )
            matrix = fitz.Matrix(scale, scale)
            pixmap = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n
            )
            yield page_number, image


def _parse_result(result: Any) -> tuple[list[dict], str]:
    payload = result.json
    if callable(payload):
        payload = payload()

    result_data = payload.get("res", payload)
    texts = _to_list(result_data.get("rec_texts"))
    scores = _to_list(result_data.get("rec_scores"))
    boxes = _to_list(result_data.get("rec_boxes"))

    lines = []
    for index, raw_text in enumerate(texts):
        text = str(raw_text).strip()
        if not text:
            continue

        confidence = float(scores[index]) if index < len(scores) else None
        bounding_box = boxes[index] if index < len(boxes) else None
        lines.append(
            {
                "text": text,
                "confidence": confidence,
                "bounding_box": bounding_box,
            }
        )

    return lines, "\n".join(line["text"] for line in lines)


def extract_text_from_image(image: np.ndarray) -> dict:
    """OCR a decoded RGB image using the same normalized line contract as PDFs."""
    predictions = list(get_ocr_engine().predict(image))
    lines = []
    text_parts = []
    for prediction in predictions:
        prediction_lines, prediction_text = _parse_result(prediction)
        lines.extend(prediction_lines)
        if prediction_text:
            text_parts.append(prediction_text)
    text = "\n".join(text_parts)
    confidences = [line["confidence"] for line in lines if line["confidence"] is not None]
    return {
        "text": text,
        "lines": lines,
        "average_confidence": sum(confidences) / len(confidences) if confidences else None,
    }


def extract_text_with_paddleocr(
    file_path: str,
    page_numbers: set[int] | None = None,
) -> dict:
    pdf_path = Path(file_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Unsupported file type: {pdf_path.suffix}. Only PDF files are supported."
        )

    engine = get_ocr_engine()
    extracted_pages = []

    for page_number, page_image in _render_pdf_pages(pdf_path, page_numbers):
        predictions = list(engine.predict(page_image))
        page_lines = []
        page_text_parts = []

        for prediction in predictions:
            lines, result_text = _parse_result(prediction)
            page_lines.extend(lines)
            if result_text:
                page_text_parts.append(result_text)

        page_text = "\n".join(page_text_parts)
        confidences = [
            line["confidence"]
            for line in page_lines
            if line["confidence"] is not None
        ]
        extracted_pages.append(
            {
                "page_number": page_number,
                "text": page_text,
                "character_count": len(page_text),
                "word_count": len(page_text.split()),
                "average_confidence": (
                    sum(confidences) / len(confidences) if confidences else None
                ),
                "lines": page_lines,
            }
        )

    full_text = "\n\n".join(
        page["text"] for page in extracted_pages if page["text"]
    )

    return {
        "text": full_text,
        "page_count": len(extracted_pages),
        "character_count": len(full_text),
        "word_count": len(full_text.split()),
        "extraction_method": "paddleocr",
        "status": "success" if full_text else "empty",
        "pages": extracted_pages,
    }
