import unittest
from unittest.mock import patch

from backend.app.extraction.extraction_pipeline import process_document


def extraction_result(method: str, status: str = "success") -> dict:
    text = "recognized document text" if status == "success" else ""
    return {
        "status": status,
        "extraction_method": method,
        "text": text,
        "page_count": 1,
        "character_count": len(text),
        "word_count": len(text.split()),
        "pages": [{"page_number": 1, "text": text}],
    }


class ExtractionPipelineTests(unittest.TestCase):
    @patch("backend.app.extraction.extraction_pipeline.extract_text_with_paddleocr")
    @patch("backend.app.extraction.extraction_pipeline.extract_text_from_pdf")
    @patch("backend.app.extraction.extraction_pipeline.predict_ocr_requirement")
    def test_routes_text_pdf_to_pymupdf(self, verdict, direct_extract, ocr_extract):
        verdict.return_value = {
            "ocr_required": "NO",
            "confidence": 0.95,
            "model_version": "test-v1",
        }
        direct_extract.return_value = extraction_result("pymupdf")

        result = process_document("document.pdf")

        self.assertEqual(result["extraction_method"], "pymupdf")
        self.assertEqual(result["ocr_required"], "NO")
        direct_extract.assert_called_once_with("document.pdf")
        ocr_extract.assert_not_called()

    @patch("backend.app.extraction.extraction_pipeline.extract_text_with_paddleocr")
    @patch("backend.app.extraction.extraction_pipeline.extract_text_from_pdf")
    @patch("backend.app.extraction.extraction_pipeline.predict_ocr_requirement")
    def test_routes_scanned_pdf_to_paddleocr(self, verdict, direct_extract, ocr_extract):
        verdict.return_value = {
            "ocr_required": "YES",
            "confidence": 0.91,
            "model_version": "test-v1",
        }
        ocr_extract.return_value = extraction_result("paddleocr")

        result = process_document("scan.pdf")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["ocr_required"], "YES")
        self.assertEqual(result["ocr_model_version"], "test-v1")
        self.assertEqual(result["extraction_method"], "paddleocr")
        ocr_extract.assert_called_once_with("scan.pdf")
        direct_extract.assert_not_called()

    @patch("backend.app.extraction.extraction_pipeline.predict_ocr_requirement")
    def test_rejects_unknown_ocr_verdict(self, verdict):
        verdict.return_value = {
            "ocr_required": "MAYBE",
            "confidence": 0.5,
            "model_version": "test-v1",
        }

        with self.assertRaisesRegex(ValueError, "Unsupported OCR verdict"):
            process_document("document.pdf")


if __name__ == "__main__":
    unittest.main()
