import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.services.document_processing import process_document_job


def make_document():
    return SimpleNamespace(
        id="document-1",
        file_path="storage/uploads/DOC-001.pdf",
        processing_status="queued",
        processing_stage="queued",
        processing_progress=0,
        processing_error=None,
        processing_started_at=None,
        processing_completed_at=None,
        extracted_text=None,
        extraction_method=None,
        ocr_required=None,
        ocr_confidence=None,
        ocr_model_version=None,
    )


def extraction_result(status="success"):
    text = "Searchable document text" if status == "success" else ""
    return {
        "status": status,
        "text": text,
        "extraction_method": "hybrid",
        "ocr_required": "YES",
        "ocr_confidence": 0.92,
        "ocr_model_version": "v1_layout",
    }


class BackgroundProcessingTests(unittest.TestCase):
    @patch("backend.app.services.document_processing.rebuild_document_index")
    @patch("backend.app.services.document_processing.process_document")
    @patch("backend.app.services.document_processing.SessionLocal")
    def test_runs_extraction_and_indexing_to_completion(
        self,
        session_factory,
        process,
        rebuild,
    ):
        document = make_document()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = document
        session_factory.return_value = db
        process.return_value = extraction_result()
        rebuild.return_value = {
            "status": "embedded",
            "chunk_count": 2,
            "embedded_chunk_count": 2,
            "embedding_model": "test-model",
        }

        result = process_document_job(document.id)

        process.assert_called_once_with(document.file_path)
        rebuild.assert_called_once_with(document, db)
        self.assertEqual(document.processing_stage, "completed")
        self.assertEqual(document.processing_progress, 100)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["embedded_chunk_count"], 2)
        db.close.assert_called_once_with()

    @patch("backend.app.services.document_processing.process_document")
    @patch("backend.app.services.document_processing.SessionLocal")
    def test_failure_is_persisted_for_user_visible_retry(
        self,
        session_factory,
        process,
    ):
        document = make_document()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = document
        session_factory.return_value = db
        process.side_effect = RuntimeError("OCR worker failed")

        with self.assertRaisesRegex(RuntimeError, "OCR worker failed"):
            process_document_job(document.id)

        self.assertEqual(document.processing_status, "processing_failed")
        self.assertEqual(document.processing_stage, "failed")
        self.assertEqual(document.processing_error, "OCR worker failed")
        db.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
