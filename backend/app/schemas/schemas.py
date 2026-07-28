from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    chunk_count: int = 0
    embedded_chunk_count: int = 0
    embedding_model: str | None = None
    created_at: datetime


class DocumentUploadAccepted(BaseModel):
    id: str
    document_id: str
    document_code: str
    original_filename: str
    saved_filename: str
    file_path: str
    content_type: str
    file_size: int
    processing_status: str
    processing_stage: str
    processing_progress: int
    worker_task_id: str
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    processing_stage: str = "queued"
    processing_progress: int = 0
    processing_error: str | None = None
    retry_count: int = 0
    worker_task_id: str | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    updated_at: datetime | None = None
    created_at: datetime


class DocumentRenameRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)

    @field_validator("filename")
    @classmethod
    def filename_must_be_safe_pdf_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or cleaned in {".", ".."}:
            raise ValueError("Filename must contain text.")
        if "/" in cleaned or "\\" in cleaned or "\x00" in cleaned:
            raise ValueError("Filename must not contain a path.")
        if not cleaned.lower().endswith(".pdf"):
            raise ValueError("Filename must use the .pdf extension.")
        return cleaned


class DocumentProcessingStatus(BaseModel):
    document_id: str
    processing_status: str
    job_status: str
    stage: str
    progress: int
    error: str | None = None
    retry_count: int
    can_retry: bool
    worker_task_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    similarity_threshold: float = Field(default=0.0, ge=-1.0, le=1.0)
    document_id: str | None = None

    @field_validator("query")
    @classmethod
    def query_must_contain_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Query must contain non-whitespace text.")
        return cleaned


class SearchResult(BaseModel):
    document_id: str
    document_code: str
    original_filename: str
    chunk_id: str
    chunk_index: int
    text: str
    preview: str
    similarity: float


class SearchResponse(BaseModel):
    query: str
    result_count: int
    embedding_model: str
    results: list[SearchResult]
