from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
from uuid import uuid4

from backend.app.db.database import get_db
from backend.app.db.models import Document
from backend.app.db.chunk_model import DocumentChunk
from backend.app.indexing.chunking_pipeline import create_document_chunks
from backend.app.schemas.schemas import DocumentResponse
from backend.app.services.file_storage import save_uploaded_file
from backend.app.extraction.ocr_decision_engine import predict_ocr_requirement
from backend.app.extraction.extraction_pipeline import process_document

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_CONTENT_TYPES = [
    "application/pdf",
]

@router.post("/upload")
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
        processing_status = "uploaded",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document

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

    verdict = predict_ocr_requirement(document.file_path)

    document.ocr_required = verdict["ocr_required"]
    document.ocr_confidence = str(verdict["confidence"])
    document.ocr_model_version = verdict["model_version"]
    document.processing_status = "ocr_checked"

    db.commit()
    db.refresh(document)

    return {
        "document_id": document.id,
        "document_code": document.document_code,
        "original_filename": document.original_filename,
        "ocr_verdict": verdict,
    }

@router.post("/{document_id}/extract")
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

    extraction_result = process_document(document.file_path)

    if extraction_result["status"] == "pending_ocr":
        document.processing_status = "pending_ocr"
        document.ocr_required = extraction_result["ocr_required"]
        document.ocr_confidence = str(extraction_result["ocr_confidence"])

        db.commit()
        db.refresh(document)

        return {
            "document_id": document.id,
            "document_code": document.document_code,
            "status": "pending_ocr",
            "message": extraction_result["message"],
            "ocr_required": extraction_result["ocr_required"],
            "ocr_confidence": extraction_result["ocr_confidence"],
        }

    document.extracted_text = extraction_result["text"]
    document.extraction_method = extraction_result["extraction_method"]
    document.ocr_required = extraction_result["ocr_required"]
    document.ocr_confidence = str(extraction_result["ocr_confidence"])
    document.processing_status = "text_extracted"

    db.commit()
    db.refresh(document)

    return {
        "document_id": document.id,
        "document_code": document.document_code,
        "status": document.processing_status,
        "ocr_required": document.ocr_required,
        "ocr_confidence": document.ocr_confidence,
        "extraction_method": document.extraction_method,
        "character_count": extraction_result["character_count"],
        "page_count": extraction_result["page_count"],
    }

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
            detail="No extracted text found. Run extraction first.",
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
        