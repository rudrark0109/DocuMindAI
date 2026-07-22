import asyncio
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from backend.app.api.documents import extract_document_text, upload_document


def make_document():
    return SimpleNamespace(
        id="document-1",
        document_code="DOC-001",
        original_filename="scan.pdf",
        saved_filename="DOC-001.pdf",
        content_type="application/pdf",
        file_size=123,
        file_path="storage/uploads/scan.pdf",
        created_at=datetime(2026, 7, 22),
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


def extraction_result(status="success", method="paddleocr", ocr_required="YES"):
    text = "Text recovered from PDF" if status == "success" else ""
    return {
        "status": status,
        "ocr_required": ocr_required,
        "ocr_confidence": 0.93,
        "ocr_model_version": "v1_layout",
        "extraction_method": method,
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

        self.assertEqual(document.extracted_text, "Text recovered from PDF")
        self.assertEqual(document.extraction_method, "paddleocr")
        self.assertEqual(document.processing_status, "text_extracted")
        self.assertEqual(document.ocr_model_version, "v1_layout")
        self.assertEqual(response["extraction_status"], "success")
        self.assertEqual(db.commit.call_count, 2)
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
        self.assertEqual(db.commit.call_count, 2)

    @patch("backend.app.api.documents.process_document")
    def test_returns_existing_result_without_duplicate_processing(self, process):
        document = make_document()
        document.processing_status = "text_extracted"
        document.extracted_text = "Already extracted"
        document.extraction_method = "pymupdf"
        document.ocr_required = "NO"
        document.ocr_confidence = "0.98"
        db = make_db(document)

        response = extract_document_text(document.id, db)

        self.assertEqual(response["processing_status"], "text_extracted")
        self.assertEqual(response["character_count"], len("Already extracted"))
        process.assert_not_called()
        db.commit.assert_not_called()

    @patch("backend.app.api.documents.process_document")
    def test_rejects_duplicate_processing_while_in_progress(self, process):
        document = make_document()
        document.processing_status = "processing"
        db = make_db(document)

        with self.assertRaises(HTTPException) as raised:
            extract_document_text(document.id, db)

        self.assertEqual(raised.exception.status_code, 409)
        process.assert_not_called()


class AutomaticUploadPipelineTests(unittest.TestCase):
    def setUp(self):
        threadpool_patcher = patch(
            "backend.app.api.documents.run_in_threadpool",
            new_callable=AsyncMock,
        )
        self.run_in_threadpool = threadpool_patcher.start()
        self.run_in_threadpool.side_effect = lambda function, *args: function(*args)
        self.addCleanup(threadpool_patcher.stop)

        self.file = SimpleNamespace(content_type="application/pdf")
        self.saved_file = {
            "document_code": "DOC-002",
            "original_filename": "uploaded.pdf",
            "saved_filename": "DOC-002.pdf",
            "file_path": "storage/uploads/DOC-002.pdf",
            "content_type": "application/pdf",
            "file_size": 456,
        }

    @patch("backend.app.api.documents.process_document")
    @patch("backend.app.api.documents.save_uploaded_file", new_callable=AsyncMock)
    def test_upload_runs_native_pdf_pipeline(self, save_file, process):
        save_file.return_value = self.saved_file
        process.return_value = extraction_result(
            method="pymupdf",
            ocr_required="NO",
        )
        db = MagicMock()

        response = asyncio.run(upload_document(self.file, db))

        process.assert_called_once_with(self.saved_file["file_path"])
        self.assertEqual(response["extraction_method"], "pymupdf")
        self.assertEqual(response["ocr_required"], "NO")
        self.assertEqual(response["processing_status"], "text_extracted")
        self.assertEqual(db.commit.call_count, 2)

    @patch("backend.app.api.documents.process_document")
    @patch("backend.app.api.documents.save_uploaded_file", new_callable=AsyncMock)
    def test_upload_runs_paddleocr_pipeline(self, save_file, process):
        save_file.return_value = self.saved_file
        process.return_value = extraction_result()
        db = MagicMock()

        response = asyncio.run(upload_document(self.file, db))

        self.assertEqual(response["extraction_method"], "paddleocr")
        self.assertEqual(response["ocr_required"], "YES")
        self.assertEqual(response["extraction_status"], "success")

    @patch("backend.app.api.documents.process_document")
    @patch("backend.app.api.documents.save_uploaded_file", new_callable=AsyncMock)
    def test_upload_persists_empty_extraction(self, save_file, process):
        save_file.return_value = self.saved_file
        process.return_value = extraction_result(status="empty")
        db = MagicMock()

        response = asyncio.run(upload_document(self.file, db))

        self.assertEqual(response["processing_status"], "text_extraction_empty")
        self.assertEqual(response["character_count"], 0)

    @patch("backend.app.api.documents.logger.exception")
    @patch("backend.app.api.documents.process_document")
    @patch("backend.app.api.documents.save_uploaded_file", new_callable=AsyncMock)
    def test_upload_persists_failure_status(
        self,
        save_file,
        process,
        _log_exception,
    ):
        save_file.return_value = self.saved_file
        process.side_effect = RuntimeError("inference failed")
        db = MagicMock()

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(upload_document(self.file, db))

        document = db.add.call_args.args[0]
        self.assertEqual(document.processing_status, "extraction_failed")
        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(raised.exception.detail["document_id"], document.id)
        self.assertEqual(db.commit.call_count, 2)


if __name__ == "__main__":
    unittest.main()
