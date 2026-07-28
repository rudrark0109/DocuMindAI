import asyncio
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from backend.app.api.documents import (
    extract_document_text,
    get_document_status,
    retry_document_processing,
    upload_document,
)
from backend.app.services.file_storage import FileTooLargeError


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
        processing_stage="queued",
        processing_progress=0,
        processing_error=None,
        retry_count=0,
        worker_task_id=None,
        processing_started_at=None,
        processing_completed_at=None,
        updated_at=None,
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
        self.file = SimpleNamespace(content_type="application/pdf")
        self.saved_file = {
            "document_code": "DOC-002",
            "original_filename": "uploaded.pdf",
            "saved_filename": "DOC-002.pdf",
            "file_path": "storage/uploads/DOC-002.pdf",
            "content_type": "application/pdf",
            "file_size": 456,
        }

    @patch("backend.app.api.documents.process_document_task")
    @patch("backend.app.api.documents.save_uploaded_file", new_callable=AsyncMock)
    def test_upload_returns_queued_document_without_running_pipeline(
        self,
        save_file,
        processing_task,
    ):
        save_file.return_value = self.saved_file
        db = MagicMock()

        response = asyncio.run(upload_document(self.file, db))

        document = db.add.call_args.args[0]
        processing_task.apply_async.assert_called_once()
        task_args = processing_task.apply_async.call_args
        self.assertEqual(task_args.kwargs["args"], [document.id])
        self.assertEqual(task_args.kwargs["task_id"], document.worker_task_id)
        self.assertEqual(response["processing_status"], "queued")
        self.assertEqual(response["processing_stage"], "queued")
        self.assertEqual(response["processing_progress"], 0)
        self.assertEqual(response["worker_task_id"], document.worker_task_id)
        self.assertEqual(db.commit.call_count, 1)

    @patch("backend.app.api.documents.delete_saved_file")
    @patch("backend.app.api.documents.process_document_task")
    @patch("backend.app.api.documents.save_uploaded_file", new_callable=AsyncMock)
    def test_upload_removes_record_and_file_when_queue_is_unavailable(
        self,
        save_file,
        processing_task,
        delete_file,
    ):
        save_file.return_value = self.saved_file
        processing_task.apply_async.side_effect = RuntimeError("Redis unavailable")
        db = MagicMock()

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(upload_document(self.file, db))

        document = db.add.call_args.args[0]
        self.assertEqual(raised.exception.status_code, 503)
        db.delete.assert_called_once_with(document)
        delete_file.assert_called_once_with(self.saved_file["file_path"])
        self.assertEqual(db.commit.call_count, 2)

    @patch("backend.app.api.documents.save_uploaded_file", new_callable=AsyncMock)
    def test_upload_rejects_oversized_file(self, save_file):
        save_file.side_effect = FileTooLargeError("File exceeds the 25 MB limit.")

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(upload_document(self.file, MagicMock()))

        self.assertEqual(raised.exception.status_code, 413)


class BackgroundStatusApiTests(unittest.TestCase):
    def test_status_reports_queued_work(self):
        document = make_document()
        document.processing_status = "queued"
        db = make_db(document)

        response = get_document_status(document.id, db)

        self.assertEqual(response["job_status"], "queued")
        self.assertEqual(response["progress"], 0)
        self.assertFalse(response["can_retry"])

    @patch("backend.app.api.documents.process_document_task")
    def test_failed_job_can_be_requeued(self, processing_task):
        document = make_document()
        document.processing_status = "processing_failed"
        document.processing_stage = "failed"
        document.processing_error = "OCR failed"
        db = make_db(document)

        response = retry_document_processing(document.id, db)

        self.assertEqual(document.processing_status, "queued")
        self.assertEqual(document.processing_stage, "queued")
        self.assertEqual(document.retry_count, 1)
        processing_task.apply_async.assert_called_once_with(
            args=[document.id],
            task_id=document.worker_task_id,
        )
        self.assertIsNotNone(document.worker_task_id)
        self.assertEqual(response["job_status"], "queued")

    @patch("backend.app.api.documents.process_document_task")
    def test_retry_records_queue_publication_failure(self, processing_task):
        document = make_document()
        document.processing_status = "processing_failed"
        document.processing_stage = "failed"
        document.processing_error = "OCR failed"
        processing_task.apply_async.side_effect = RuntimeError("Redis unavailable")
        db = make_db(document)

        with self.assertRaises(HTTPException) as raised:
            retry_document_processing(document.id, db)

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(document.processing_status, "processing_failed")
        self.assertEqual(document.processing_stage, "failed")
        self.assertEqual(
            document.processing_error,
            "Document processing queue is unavailable.",
        )
        self.assertEqual(db.commit.call_count, 2)

    def test_active_job_cannot_be_retried(self):
        document = make_document()
        document.processing_status = "processing"
        document.processing_stage = "extracting"
        db = make_db(document)

        with self.assertRaises(HTTPException) as raised:
            retry_document_processing(document.id, db)

        self.assertEqual(raised.exception.status_code, 409)

if __name__ == "__main__":
    unittest.main()
