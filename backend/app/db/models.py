from datetime import datetime
from sqlalchemy import DateTime, Column, Integer, String, Text

from backend.app.db.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    document_code = Column(String, unique=True, index=True, nullable=False)
    original_filename = Column(String, nullable=False)
    saved_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String, default="uploaded", nullable=False)
    ocr_required = Column(String, nullable=True)
    ocr_confidence = Column(String, nullable=True)
    ocr_model_version = Column(String, nullable=True)
    extracted_text = Column(Text, nullable=True)
    extraction_method = Column(String, nullable=True)
    processing_stage = Column(String, default="queued", nullable=False)
    processing_progress = Column(Integer, default=0, nullable=False)
    processing_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    worker_task_id = Column(String, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
