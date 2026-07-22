from backend.app.extraction.ocr_decision_engine import predict_ocr_requirement
from backend.app.extraction.paddle_ocr_extractor import extract_text_with_paddleocr
from backend.app.extraction.pdf_extractor import extract_text_from_pdf


def process_document(file_path: str) -> dict:
    """
    Process a document and determine the best extraction strategy.
    """

    ocr_verdict = predict_ocr_requirement(file_path)

    ocr_required = ocr_verdict["ocr_required"]
    if ocr_required == "NO":
        extraction_result = extract_text_from_pdf(file_path)
    elif ocr_required == "YES":
        extraction_result = extract_text_with_paddleocr(file_path)
    else:
        raise ValueError(f"Unsupported OCR verdict: {ocr_required}")

    return {
        "status": extraction_result["status"],
        "ocr_required": ocr_required,
        "ocr_confidence": ocr_verdict["confidence"],
        "ocr_model_version": ocr_verdict["model_version"],
        "extraction_method": extraction_result["extraction_method"],
        "text": extraction_result["text"],
        "page_count": extraction_result["page_count"],
        "character_count": extraction_result["character_count"],
        "word_count": extraction_result["word_count"],
        "pages": extraction_result["pages"],
    }
