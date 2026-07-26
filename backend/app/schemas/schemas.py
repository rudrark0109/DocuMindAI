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
    created_at: datetime


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
