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
    scale = settings.ocr_render_dpi / 72
    matrix = fitz.Matrix(scale, scale)

    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            if page_numbers is not None and page_number not in page_numbers:
                continue
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
