import logging
import json
from datetime import datetime, timezone

from backend.app.db.database import SessionLocal
from backend.app.db.models import Document
from backend.app.extraction.extraction_pipeline import process_document
from backend.app.indexing.indexing_pipeline import rebuild_document_index


logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _persist_extraction_result(document: Document, extraction_result: dict) -> None:
    document.extracted_text = extraction_result["text"]
    document.extracted_pages = json.dumps(extraction_result.get("pages", []))
    document.normalized_blocks = json.dumps(extraction_result.get("blocks", []))
    document.extraction_warnings = json.dumps(extraction_result.get("warnings", []))
    document.source_format = extraction_result.get("source_format")
    document.extraction_method = extraction_result["extraction_method"]
    document.ocr_required = extraction_result["ocr_required"]
    document.ocr_confidence = (
        str(extraction_result["ocr_confidence"])
        if extraction_result["ocr_confidence"] is not None
        else None
    )
    document.ocr_model_version = extraction_result["ocr_model_version"]


def process_document_job(document_id: str) -> dict:
    """Run the existing extraction and indexing pipeline outside the API process."""
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise ValueError(f"Document {document_id} does not exist.")
        if document.processing_status == "embedded":
            return {"document_id": document_id, "status": "already_completed"}

        document.processing_status = "processing"
        document.processing_stage = "extracting"
        document.processing_progress = 10
        document.processing_error = None
        document.processing_started_at = _now()
        document.processing_completed_at = None
        db.commit()

        extraction_result = process_document(document.file_path)
        _persist_extraction_result(document, extraction_result)
        document.processing_progress = 65

        if extraction_result["status"] != "success":
            document.processing_status = "text_extraction_empty"
            document.processing_stage = "completed"
            document.processing_progress = 100
            document.processing_completed_at = _now()
            db.commit()
            return {"document_id": document_id, "status": "completed_empty"}

        document.processing_stage = "indexing"
        db.commit()
        indexing_result = rebuild_document_index(document, db)

        document.processing_stage = "completed"
        document.processing_progress = 100
        document.processing_completed_at = _now()
        document.processing_error = None
        db.commit()
        return {
            **indexing_result,
            "document_id": document_id,
            "status": "completed",
        }
    except Exception as exc:
        db.rollback()
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is not None:
            document.processing_status = "processing_failed"
            document.processing_stage = "failed"
            document.processing_error = str(exc)[:4000]
            document.processing_completed_at = _now()
            db.commit()
        logger.exception(
            "Background document processing failed",
            extra={"document_id": document_id},
        )
        raise
    finally:
        db.close()
