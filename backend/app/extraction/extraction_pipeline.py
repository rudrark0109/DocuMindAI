from backend.app.extraction.ocr_decision_engine import predict_ocr_requirement
from backend.app.extraction.pdf_extractor import extract_text_from_pdf


def process_document(file_path: str) -> dict:
    """
    Process a document and determine the best extraction strategy.
    """

    ocr_verdict = predict_ocr_requirement(file_path)

    if ocr_verdict["ocr_required"] == "NO":

        extraction_result = extract_text_from_pdf(file_path)

        return {
            "status": "success",
            "ocr_required": "NO",
            "ocr_confidence": ocr_verdict["confidence"],
            "extraction_method": extraction_result["extraction_method"],
            "text": extraction_result["text"],
            "page_count": extraction_result["page_count"],
            "character_count": extraction_result["character_count"],
        }

    return {
        "status": "pending_ocr",
        "ocr_required": "YES",
        "ocr_confidence": ocr_verdict["confidence"],
        "message": "OCR extraction pipeline not implemented yet.",
    }