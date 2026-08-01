import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import uuid4

from backend.app.db.database import get_db
from backend.app.db.models import Document
from backend.app.db.chunk_model import DocumentChunk
from backend.app.indexing.chunking_pipeline import create_document_chunks
from backend.app.schemas.schemas import (
    DocumentProcessingResponse,
    DocumentProcessingStatus,
    DocumentRenameRequest,
    DocumentResponse,
    DocumentUploadAccepted,
)
from backend.app.services.file_storage import (
    FileTooLargeError,
    delete_saved_file,
    save_uploaded_file,
)
from backend.app.extraction.ocr_decision_engine import predict_ocr_requirement
from backend.app.extraction.extraction_pipeline import process_document
from backend.app.indexing.embedding_pipeline import embed_document_chunks
from backend.app.worker.tasks import process_document_task

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/csv",
    "image/png",
    "image/jpeg",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".png", ".jpg", ".jpeg"}

COMPLETED_EXTRACTION_STATUSES = {"text_extracted", "text_extraction_empty"}


def _persist_extraction_result(document: Document, extraction_result: dict) -> None:
    """Copy a normalized extraction result onto its document record."""

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
    document.processing_status = (
        "text_extracted"
        if extraction_result["status"] == "success"
        else "text_extraction_empty"
    )


def _processing_response(
    document: Document,
    extraction_result: dict | None = None,
    indexing_result: dict | None = None,
) -> dict:
    """Build the shared response returned by automatic and manual extraction."""

    text = document.extracted_text or ""
    extraction_status = (
        extraction_result["status"]
        if extraction_result is not None
        else ("success" if document.processing_status == "text_extracted" else "empty")
    )

    return {
        "id": document.id,
        "document_id": document.id,
        "document_code": document.document_code,
        "original_filename": document.original_filename,
        "saved_filename": document.saved_filename,
        "file_path": document.file_path,
        "content_type": document.content_type,
        "file_size": document.file_size,
        "processing_status": document.processing_status,
        "extraction_status": extraction_status,
        "ocr_required": document.ocr_required,
        "ocr_confidence": (
            float(document.ocr_confidence)
            if document.ocr_confidence is not None
            else None
        ),
        "extraction_method": document.extraction_method,
        "character_count": (
            extraction_result["character_count"]
            if extraction_result is not None
            else len(text)
        ),
        "word_count": (
            extraction_result["word_count"]
            if extraction_result is not None
            else len(text.split())
        ),
        "page_count": (
            extraction_result["page_count"]
            if extraction_result is not None
            else None
        ),
        "created_at": document.created_at,
        "chunk_count": indexing_result["chunk_count"] if indexing_result else 0,
        "embedded_chunk_count": (
            indexing_result["embedded_chunk_count"] if indexing_result else 0
        ),
        "embedding_model": (
            indexing_result["embedding_model"] if indexing_result else None
        ),
    }


def _mark_extraction_failed(document: Document, db: Session) -> None:
    document.processing_status = "extraction_failed"
    db.commit()
    logger.exception(
        "Document extraction failed",
        extra={"document_id": document.id},
    )


@router.post(
    "/upload",
    response_model=DocumentUploadAccepted,
    status_code=202,
    summary="Upload and queue a document for background processing",
    description=(
        "Validates and stores the document, creates its metadata record, and queues "
        "selective OCR, text extraction, chunking, and embedding for a worker."
    ),
)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    default_extension = ".pdf" if getattr(file, "content_type", None) == "application/pdf" else ""
    extension = Path(getattr(file, "filename", None) or f"document{default_extension}").suffix.lower()
    if file.content_type not in ALLOWED_CONTENT_TYPES or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, TXT, Markdown, CSV, PNG, JPG, or JPEG.")

    try:
        saved_file_info = await save_uploaded_file(file)
    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    
    task_id = str(uuid4())
    document = Document(
        id=str(uuid4()),
        document_code=saved_file_info["document_code"],
        original_filename=saved_file_info["original_filename"],
        saved_filename=saved_file_info["saved_filename"],
        file_path=saved_file_info["file_path"],
        content_type=saved_file_info["content_type"],
        file_size=int(saved_file_info["file_size"]),
        processing_status="queued",
        processing_stage="queued",
        processing_progress=0,
        worker_task_id=task_id,
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        delete_saved_file(document.file_path)
        raise

    try:
        process_document_task.apply_async(args=[document.id], task_id=task_id)
    except Exception as exc:
        db.rollback()
        db.delete(document)
        db.commit()
        delete_saved_file(document.file_path)
        raise HTTPException(
            status_code=503,
            detail="Document processing queue is unavailable. Please try again.",
        ) from exc

    return {
        "id": document.id,
        "document_id": document.id,
        "document_code": document.document_code,
        "original_filename": document.original_filename,
        "saved_filename": document.saved_filename,
        "file_path": document.file_path,
        "content_type": document.content_type,
        "file_size": document.file_size,
        "processing_status": document.processing_status,
        "processing_stage": document.processing_stage,
        "processing_progress": document.processing_progress,
        "worker_task_id": document.worker_task_id,
        "created_at": document.created_at,
    }

@router.get("", response_model=list[DocumentResponse])
def get_all_documents(db: Session = Depends(get_db)):
    documents = (db.query(Document).order_by(Document.created_at.desc()).all())
    return documents

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_by_id(document_id: str, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get(
    "/{document_id}/file",
    response_class=FileResponse,
    summary="View or download a stored PDF",
)
def get_document_file(document_id: str, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = Path(document.file_path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Stored PDF is unavailable.")

    return FileResponse(
        path=str(file_path),
        media_type=getattr(document, "content_type", "application/pdf"),
        filename=document.original_filename,
        content_disposition_type="inline",
    )


def _job_status(document: Document) -> str:
    if document.processing_stage == "failed" or document.processing_status.endswith(
        "_failed"
    ):
        return "failed"
    if document.processing_stage == "completed" or document.processing_status in {
        "embedded",
        "text_extraction_empty",
    }:
        return "completed"
    if document.processing_status == "queued":
        return "queued"
    return "processing"


@router.get(
    "/{document_id}/status",
    response_model=DocumentProcessingStatus,
    summary="Get background processing status",
)
def get_document_status(document_id: str, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    job_status = _job_status(document)
    return {
        "document_id": document.id,
        "processing_status": document.processing_status,
        "job_status": job_status,
        "stage": document.processing_stage,
        "progress": document.processing_progress,
        "error": document.processing_error,
        "retry_count": document.retry_count,
        "can_retry": job_status == "failed",
        "worker_task_id": document.worker_task_id,
        "started_at": document.processing_started_at,
        "completed_at": document.processing_completed_at,
        "updated_at": document.updated_at,
    }


@router.post(
    "/{document_id}/retry",
    response_model=DocumentProcessingStatus,
    status_code=202,
    summary="Retry failed background processing",
)
def retry_document_processing(document_id: str, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if _job_status(document) != "failed":
        raise HTTPException(
            status_code=409,
            detail="Only failed document processing jobs can be retried.",
        )

    document.processing_status = "queued"
    document.processing_stage = "queued"
    document.processing_progress = 0
    document.processing_error = None
    document.processing_started_at = None
    document.processing_completed_at = None
    document.retry_count += 1
    task_id = str(uuid4())
    document.worker_task_id = task_id
    try:
        db.commit()
        db.refresh(document)
        process_document_task.apply_async(args=[document.id], task_id=task_id)
    except Exception as exc:
        db.rollback()
        document.processing_status = "processing_failed"
        document.processing_stage = "failed"
        document.processing_error = "Document processing queue is unavailable."
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Document processing queue is unavailable. Please try again.",
        ) from exc

    return get_document_status(document_id, db)


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Rename a stored document",
)
def rename_document(
    document_id: str,
    request: DocumentRenameRequest,
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    document.original_filename = request.filename
    db.commit()
    db.refresh(document)
    return document


@router.delete(
    "/{document_id}",
    status_code=204,
    summary="Delete a stored document",
)
def delete_document(document_id: str, db: Session = Depends(get_db)) -> Response:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = document.file_path
    try:
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete(synchronize_session=False)
        db.delete(document)
        db.commit()
    except Exception:
        db.rollback()
        raise

    try:
        delete_saved_file(file_path)
    except OSError:
        logger.exception(
            "Document metadata was deleted but its stored file could not be removed",
            extra={"document_id": document_id, "file_path": file_path},
        )

    return Response(status_code=204)

@router.post("/{document_id}/ocr-verdict")
def get_ocr_verdict(
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    Run OCR Decision Engine on an uploaded PDF and return OCR verdict.
    """

    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    if document.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="OCR verdict currently supports PDF documents only.",
        )

    if document.ocr_required is not None:
        verdict = {
            "ocr_required": document.ocr_required,
            "confidence": (
                float(document.ocr_confidence)
                if document.ocr_confidence is not None
                else None
            ),
            "model_version": document.ocr_model_version,
        }
    else:
        verdict = predict_ocr_requirement(document.file_path)
        document.ocr_required = verdict["ocr_required"]
        document.ocr_confidence = str(verdict["confidence"])
        document.ocr_model_version = verdict["model_version"]
        if document.processing_status == "uploaded":
            document.processing_status = "ocr_checked"

        db.commit()
        db.refresh(document)

    return {
        "document_id": document.id,
        "document_code": document.document_code,
        "original_filename": document.original_filename,
        "ocr_verdict": verdict,
    }

@router.post(
    "/{document_id}/extract",
    response_model=DocumentProcessingResponse,
    summary="Retry extraction or return the existing extraction result",
)
def extract_document_text(
    document_id: str,
    db: Session = Depends(get_db),
):
   

    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    if document.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Text extraction currently supports PDF documents only.",
        )

    if document.processing_status in COMPLETED_EXTRACTION_STATUSES:
        return _processing_response(document)

    if document.processing_status == "processing":
        raise HTTPException(
            status_code=409,
            detail="Document extraction is already in progress.",
        )

    document.processing_status = "processing"
    db.commit()

    try:
        extraction_result = process_document(document.file_path)
    except Exception as exc:
        _mark_extraction_failed(document, db)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Document extraction failed.",
                "document_id": document.id,
                "processing_status": document.processing_status,
            },
        ) from exc

    _persist_extraction_result(document, extraction_result)

    db.commit()
    db.refresh(document)

    return _processing_response(document, extraction_result)

@router.get("/{document_id}/text")
def get_document_text(
    document_id: str,
    db: Session = Depends(get_db),
):

    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    if not document.extracted_text:
        raise HTTPException(
            status_code=404,
            detail="No extracted text is available for this document.",
        )

    return {
        "document_id": document.id,
        "document_code": document.document_code,
        "original_filename": document.original_filename,
        "extraction_method": document.extraction_method,
        "processing_status": document.processing_status,
        "text": document.extracted_text,
    }

@router.post("/{document_id}/chunk")
def chunk_document_text(document_id: str, db: Session = Depends(get_db)):
    document = (db.query(Document).filter(Document.id == document_id).first())

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    if not document.extracted_text:
        raise HTTPException(status_code=400, detail="Document has no extracted text to chunk. Run extraction first.")
    
    existing_chunks = (db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).count())
    if existing_chunks > 0:
        raise HTTPException(status_code=400, detail="Document has already been chunked.")
        
    chunk_result = create_document_chunks(document)

    for chunk in chunk_result["chunks"]:
        chunk_record = DocumentChunk(
            id=str(uuid4()),
            document_id=document.id,
            chunk_index=chunk["chunk_index"],
            chunk_text=chunk["text"],
            word_count=chunk["word_count"],
            character_count=chunk["char_count"],
            start_word_index=chunk["start_word_index"],
            end_word_index=chunk["end_word_index"],
        )

        db.add(chunk_record)

    document.processing_status = "text_chunked"
    db.commit()
    db.refresh(document)

    return {
        "document_id": document.id,
        "document_code": document.document_code,
        "processing_status": document.processing_status,
        "chunk_count": chunk_result["chunk_count"],
    }

@router.post("/{document_id}/embed")
def embed_document(document_id: str, db: Session = Depends(get_db)):
    document = (db.query(Document).filter(Document.id == document_id).first())
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).count()
    if chunk_count == 0:
        raise HTTPException(status_code=400, detail="Document has no chunks to embed. Run chunking first.")
    
    embedding_result = embed_document_chunks(document_id, db)

    if embedding_result["status"] == "embedded":
        document.processing_status = "embedded"
        db.commit()
        db.refresh(document)

    return{
        "document_id": document.id,
        "document_code": document.document_code,
        "processing_status": document.processing_status,
        "embedding_result": embedding_result,
    }
