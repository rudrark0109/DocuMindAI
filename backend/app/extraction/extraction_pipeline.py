from backend.app.extraction.ocr_decision_engine import predict_page_ocr_requirements
from backend.app.extraction.paddle_ocr_extractor import extract_text_with_paddleocr
from backend.app.extraction.pdf_extractor import extract_text_from_pdf


def process_document(file_path: str) -> dict:
    """
    Process a document and determine the best extraction strategy.
    """

    page_verdicts = predict_page_ocr_requirements(file_path)
    if not page_verdicts:
        raise ValueError("Cannot process a PDF with no pages.")

    unsupported_verdicts = {
        verdict["ocr_required"]
        for verdict in page_verdicts
        if verdict["ocr_required"] not in {"YES", "NO"}
    }
    if unsupported_verdicts:
        raise ValueError(
            f"Unsupported OCR verdict: {', '.join(sorted(unsupported_verdicts))}"
        )

    ocr_page_numbers = {
        verdict["page_number"]
        for verdict in page_verdicts
        if verdict["ocr_required"] == "YES"
    }
    native_page_numbers = {
        verdict["page_number"]
        for verdict in page_verdicts
        if verdict["ocr_required"] == "NO"
    }

    pages_by_number = {}
    if native_page_numbers:
        native_result = extract_text_from_pdf(file_path)
        pages_by_number.update(
            {
                page["page_number"]: {**page, "extraction_method": "pymupdf"}
                for page in native_result["pages"]
                if page["page_number"] in native_page_numbers
            }
        )

    if ocr_page_numbers:
        ocr_result = extract_text_with_paddleocr(file_path, ocr_page_numbers)
        pages_by_number.update(
            {
                page["page_number"]: {**page, "extraction_method": "paddleocr"}
                for page in ocr_result["pages"]
            }
        )

    verdicts_by_page = {
        verdict["page_number"]: verdict for verdict in page_verdicts
    }
    extracted_pages = []
    for page_number in sorted(verdicts_by_page):
        verdict = verdicts_by_page[page_number]
        page = pages_by_number.get(
            page_number,
            {
                "page_number": page_number,
                "text": "",
                "character_count": 0,
                "word_count": 0,
                "extraction_method": (
                    "paddleocr" if verdict["ocr_required"] == "YES" else "pymupdf"
                ),
            },
        )
        extracted_pages.append(
            {
                **page,
                "ocr_required": verdict["ocr_required"],
                "ocr_confidence": verdict["confidence"],
                "ocr_model_version": verdict["model_version"],
            }
        )

    full_text = "\n\n".join(
        page["text"] for page in extracted_pages if page["text"]
    )
    confidences = [
        verdict["confidence"]
        for verdict in page_verdicts
        if verdict["confidence"] is not None
    ]
    ocr_required = "YES" if ocr_page_numbers else "NO"
    if ocr_page_numbers and native_page_numbers:
        extraction_method = "hybrid"
    elif ocr_page_numbers:
        extraction_method = "paddleocr"
    else:
        extraction_method = "pymupdf"

    return {
        "status": "success" if full_text else "empty",
        "ocr_required": ocr_required,
        "ocr_confidence": (
            sum(confidences) / len(confidences) if confidences else None
        ),
        "ocr_model_version": page_verdicts[0]["model_version"],
        "extraction_method": extraction_method,
        "text": full_text,
        "page_count": len(extracted_pages),
        "character_count": len(full_text),
        "word_count": len(full_text.split()),
        "pages": extracted_pages,
    }
