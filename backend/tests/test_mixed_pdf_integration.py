import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.extraction.extraction_pipeline import process_document
from backend.app.extraction.ocr_decision_engine import predict_page_ocr_requirements
from backend.app.extraction.pdf_feature_extractor import extract_pdf_page_features
from backend.tests.mixed_pdf_fixture import create_mixed_pdf
from backend.tests.test_paddle_ocr_extractor import FakeEngine


class MixedPdfIntegrationTests(unittest.TestCase):
    def test_model_routes_native_and_scanned_fixture_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "mixed.pdf"
            create_mixed_pdf(pdf_path)

            verdicts = predict_page_ocr_requirements(str(pdf_path))

        self.assertEqual(
            [verdict["ocr_required"] for verdict in verdicts],
            ["NO", "YES"],
        )

    def test_fixture_contains_native_and_image_only_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "mixed.pdf"
            create_mixed_pdf(pdf_path)

            pages = extract_pdf_page_features(str(pdf_path))

        self.assertGreater(pages[0]["features"]["char_count"], 0)
        self.assertEqual(pages[1]["features"]["char_count"], 0)
        self.assertGreaterEqual(pages[1]["features"]["image_count"], 1)

    @patch("backend.app.extraction.paddle_ocr_extractor.get_ocr_engine")
    @patch(
        "backend.app.extraction.extraction_pipeline.predict_page_ocr_requirements"
    )
    def test_real_mixed_pdf_preserves_order_and_ocr_selectivity(
        self,
        predict,
        get_engine,
    ):
        predict.return_value = [
            {
                "page_number": 1,
                "ocr_required": "NO",
                "confidence": 0.98,
                "model_version": "fixture-v1",
            },
            {
                "page_number": 2,
                "ocr_required": "YES",
                "confidence": 0.96,
                "model_version": "fixture-v1",
            },
        ]
        engine = FakeEngine()
        get_engine.return_value = engine

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "mixed.pdf"
            create_mixed_pdf(pdf_path)
            result = process_document(str(pdf_path))

        self.assertEqual(result["extraction_method"], "hybrid")
        self.assertEqual(engine.calls, 1)
        self.assertEqual(
            [page["page_number"] for page in result["pages"]],
            [1, 2],
        )
        self.assertIn("NATIVE PAGE", result["pages"][0]["text"])
        self.assertIn("recognized text", result["pages"][1]["text"])
        self.assertLess(
            result["text"].index("NATIVE PAGE"),
            result["text"].index("recognized text"),
        )


if __name__ == "__main__":
    unittest.main()
