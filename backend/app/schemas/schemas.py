from datetime import datetime
from pydantic import BaseModel


class DocumentProcessingResponse(BaseModel):
    id: str
    document_id: str
    document_code: str
    original_filename: str
    saved_filename: str
    file_path: str
    content_type: str
    file_size: int
    processing_status: str
    extraction_status: str
    ocr_required: str | None = None
    ocr_confidence: float | None = None
    extraction_method: str | None = None
    character_count: int = 0
    word_count: int = 0
    page_count: int | None = None
    created_at: datetime


class DocumentResponse(BaseModel):
    id: str
    document_code: str
    original_filename: str
    saved_filename: str
    file_path: str
    content_type: str
    file_size: int
    processing_status: str
    ocr_required: str | None = None
    ocr_confidence: float | None = None
    ocr_model_version: str | None = None
    extraction_method: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
