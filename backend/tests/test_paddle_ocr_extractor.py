import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.extraction.paddle_ocr_extractor import (
    _parse_result,
    extract_text_with_paddleocr,
    get_ocr_engine,
)


class FakeResult:
    def __init__(self, texts, scores, boxes):
        self.json = {
            "res": {
                "rec_texts": texts,
                "rec_scores": scores,
                "rec_boxes": boxes,
            }
        }


class FakeEngine:
    def __init__(self):
        self.calls = 0

    def predict(self, _image):
        self.calls += 1
        return [
            FakeResult(
                [f"Page {self.calls}", "recognized text"],
                [0.99, 0.88],
                [[1, 2, 3, 4], [5, 6, 7, 8]],
            )
        ]


class PaddleOCRExtractorTests(unittest.TestCase):
    def test_disables_mkldnn_for_cpu_runtime_compatibility(self):
        paddle_ocr = MagicMock(return_value=object())
        fake_module = SimpleNamespace(PaddleOCR=paddle_ocr)
        get_ocr_engine.cache_clear()

        with patch.dict(sys.modules, {"paddleocr": fake_module}):
            get_ocr_engine()

        self.assertFalse(paddle_ocr.call_args.kwargs["enable_mkldnn"])
        get_ocr_engine.cache_clear()

    def test_parse_result_normalizes_lines(self):
        lines, text = _parse_result(
            FakeResult([" Hello ", "", "world"], [0.9, 0.5, 0.8], [])
        )

        self.assertEqual(text, "Hello\nworld")
        self.assertEqual([line["confidence"] for line in lines], [0.9, 0.8])

    def test_extracts_each_rendered_page(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as pdf_file:
            rendered_pages = [(1, object()), (2, object())]
            engine = FakeEngine()

            with (
                patch(
                    "backend.app.extraction.paddle_ocr_extractor._render_pdf_pages",
                    return_value=rendered_pages,
                ),
                patch(
                    "backend.app.extraction.paddle_ocr_extractor.get_ocr_engine",
                    return_value=engine,
                ),
            ):
                result = extract_text_with_paddleocr(pdf_file.name)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["extraction_method"], "paddleocr")
        self.assertEqual(result["page_count"], 2)
        self.assertEqual(engine.calls, 2)
        self.assertIn("Page 1", result["text"])
        self.assertIn("Page 2", result["text"])
        self.assertAlmostEqual(result["pages"][0]["average_confidence"], 0.935)

    def test_rejects_non_pdf_files(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as text_file:
            with self.assertRaises(ValueError):
                extract_text_with_paddleocr(text_file.name)


if __name__ == "__main__":
    unittest.main()
