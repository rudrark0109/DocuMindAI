import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from uuid import uuid4

from backend.app.db.database import get_db
from backend.app.db.models import Document
from backend.app.db.chunk_model import DocumentChunk
from backend.app.indexing.chunking_pipeline import create_document_chunks
from backend.app.schemas.schemas import DocumentProcessingResponse, DocumentResponse
from backend.app.services.file_storage import save_uploaded_file
from backend.app.extraction.ocr_decision_engine import predict_ocr_requirement
from backend.app.extraction.extraction_pipeline import process_document
from backend.app.indexing.embedding_pipeline import embed_document_chunks

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = [
    "application/pdf",
]

COMPLETED_EXTRACTION_STATUSES = {"text_extracted", "text_extraction_empty"}


def _persist_extraction_result(document: Document, extraction_result: dict) -> None:
    """Copy a normalized extraction result onto its document record."""

    document.extracted_text = extraction_result["text"]
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
    response_model=DocumentProcessingResponse,
    status_code=201,
    summary="Upload and automatically process a PDF",
    description=(
        "Stores the PDF, decides whether OCR is required, routes it to PyMuPDF "
        "or PaddleOCR, and persists the extracted text in one request."
    ),
)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")

    saved_file_info = await save_uploaded_file(file)
    
    document = Document(
        id = str(uuid4()),
        document_code = saved_file_info["document_code"],
        original_filename = saved_file_info["original_filename"],
        saved_filename = saved_file_info["saved_filename"],
        file_path = saved_file_info["file_path"],
        content_type = saved_file_info["content_type"],
        file_size = int(saved_file_info["file_size"]),
        processing_status = "processing",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        extraction_result = await run_in_threadpool(
            process_document,
            document.file_path,
        )
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
