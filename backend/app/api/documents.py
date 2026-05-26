from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
from uuid import uuid4

from backend.app.db.database import get_db
from backend.app.db.models import Document
from backend.app.schemas.schemas import DocumentResponse
from backend.app.services.file_storage import save_uploaded_file

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg"
]

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF and image files (JPEG, PNG, JPG) are allowed.")

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
