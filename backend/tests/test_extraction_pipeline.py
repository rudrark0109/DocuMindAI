import unittest
from unittest.mock import patch

from backend.app.extraction.extraction_pipeline import process_document


def extraction_result(
    method: str,
    page_number: int = 1,
    text: str = "recognized document text",
) -> dict:
    return {
        "status": "success" if text else "empty",
        "extraction_method": method,
        "text": text,
        "page_count": 1,
        "character_count": len(text),
        "word_count": len(text.split()),
        "pages": [
            {
                "page_number": page_number,
                "text": text,
                "character_count": len(text),
                "word_count": len(text.split()),
            }
        ],
    }


class ExtractionPipelineTests(unittest.TestCase):
    @patch("backend.app.extraction.extraction_pipeline.extract_text_with_paddleocr")
    @patch("backend.app.extraction.extraction_pipeline.extract_text_from_pdf")
    @patch("backend.app.extraction.extraction_pipeline.predict_page_ocr_requirements")
    def test_routes_text_pdf_to_pymupdf(self, verdict, direct_extract, ocr_extract):
        verdict.return_value = [{
            "page_number": 1,
            "ocr_required": "NO",
            "confidence": 0.95,
            "model_version": "test-v1",
        }]
        direct_extract.return_value = extraction_result("pymupdf")

        result = process_document("document.pdf")

        self.assertEqual(result["extraction_method"], "pymupdf")
        self.assertEqual(result["ocr_required"], "NO")
        direct_extract.assert_called_once_with("document.pdf")
        ocr_extract.assert_not_called()

    @patch("backend.app.extraction.extraction_pipeline.extract_text_with_paddleocr")
    @patch("backend.app.extraction.extraction_pipeline.extract_text_from_pdf")
    @patch("backend.app.extraction.extraction_pipeline.predict_page_ocr_requirements")
    def test_routes_scanned_pdf_to_paddleocr(self, verdict, direct_extract, ocr_extract):
        verdict.return_value = [{
            "page_number": 1,
            "ocr_required": "YES",
            "confidence": 0.91,
            "model_version": "test-v1",
        }]
        ocr_extract.return_value = extraction_result("paddleocr")

        result = process_document("scan.pdf")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["ocr_required"], "YES")
        self.assertEqual(result["ocr_model_version"], "test-v1")
        self.assertEqual(result["extraction_method"], "paddleocr")
        ocr_extract.assert_called_once_with("scan.pdf", {1})
        direct_extract.assert_not_called()

    @patch("backend.app.extraction.extraction_pipeline.predict_page_ocr_requirements")
    def test_rejects_unknown_ocr_verdict(self, verdict):
        verdict.return_value = [{
            "page_number": 1,
            "ocr_required": "MAYBE",
            "confidence": 0.5,
            "model_version": "test-v1",
        }]

        with self.assertRaisesRegex(ValueError, "Unsupported OCR verdict"):
            process_document("document.pdf")

    @patch("backend.app.extraction.extraction_pipeline.extract_text_with_paddleocr")
    @patch("backend.app.extraction.extraction_pipeline.extract_text_from_pdf")
    @patch("backend.app.extraction.extraction_pipeline.predict_page_ocr_requirements")
    def test_merges_mixed_pages_in_order_without_duplicate_text(
        self,
        verdict,
        direct_extract,
        ocr_extract,
    ):
        verdict.return_value = [
            {
                "page_number": 1,
                "ocr_required": "NO",
                "confidence": 0.97,
                "model_version": "test-v1",
            },
            {
                "page_number": 2,
                "ocr_required": "YES",
                "confidence": 0.93,
                "model_version": "test-v1",
            },
        ]
        direct_extract.return_value = {
            **extraction_result("pymupdf", 1, "native page"),
            "page_count": 2,
            "pages": [
                extraction_result("pymupdf", 1, "native page")["pages"][0],
                extraction_result("pymupdf", 2, "weak native text")["pages"][0],
            ],
        }
        ocr_extract.return_value = extraction_result(
            "paddleocr", 2, "recognized scan"
        )

        result = process_document("mixed.pdf")

        self.assertEqual(result["extraction_method"], "hybrid")
        self.assertEqual(result["text"], "native page\n\nrecognized scan")
        self.assertEqual(
            [page["page_number"] for page in result["pages"]], [1, 2]
        )
        self.assertEqual(
            [page["extraction_method"] for page in result["pages"]],
            ["pymupdf", "paddleocr"],
        )
        self.assertNotIn("weak native text", result["text"])
        ocr_extract.assert_called_once_with("mixed.pdf", {2})


if __name__ == "__main__":
    unittest.main()
