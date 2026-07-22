import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from backend.app.api.documents import extract_document_text


def make_document():
    return SimpleNamespace(
        id="document-1",
        document_code="DOC-001",
        content_type="application/pdf",
        file_path="storage/uploads/scan.pdf",
        extracted_text=None,
        extraction_method=None,
        ocr_required=None,
        ocr_confidence=None,
        ocr_model_version=None,
        processing_status="uploaded",
    )


def make_db(document):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = document
    return db


def extraction_result(status="success"):
    text = "Text recovered by OCR" if status == "success" else ""
    return {
        "status": status,
        "ocr_required": "YES",
        "ocr_confidence": 0.93,
        "ocr_model_version": "v1_layout",
        "extraction_method": "paddleocr",
        "text": text,
        "page_count": 1,
        "character_count": len(text),
        "word_count": len(text.split()),
        "pages": [{"page_number": 1, "text": text}],
    }


class DocumentExtractionAPITests(unittest.TestCase):
    @patch("backend.app.api.documents.process_document")
    def test_persists_successful_paddleocr_result(self, process):
        document = make_document()
        db = make_db(document)
        process.return_value = extraction_result()

        response = extract_document_text(document.id, db)

        self.assertEqual(document.extracted_text, "Text recovered by OCR")
        self.assertEqual(document.extraction_method, "paddleocr")
        self.assertEqual(document.processing_status, "text_extracted")
        self.assertEqual(document.ocr_model_version, "v1_layout")
        self.assertEqual(response["extraction_status"], "success")
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(document)

    @patch("backend.app.api.documents.process_document")
    def test_marks_empty_ocr_result(self, process):
        document = make_document()
        db = make_db(document)
        process.return_value = extraction_result(status="empty")

        response = extract_document_text(document.id, db)

        self.assertEqual(document.extracted_text, "")
        self.assertEqual(document.processing_status, "text_extraction_empty")
        self.assertEqual(response["extraction_status"], "empty")

    @patch("backend.app.api.documents.logger.exception")
    @patch("backend.app.api.documents.process_document")
    def test_marks_failed_extraction(self, process, _log_exception):
        document = make_document()
        db = make_db(document)
        process.side_effect = RuntimeError("OCR inference failed")

        with self.assertRaises(HTTPException) as raised:
            extract_document_text(document.id, db)

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(document.processing_status, "extraction_failed")
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
