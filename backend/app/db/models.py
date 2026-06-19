from datetime import datetime
from sqlalchemy import DateTime, Column, Integer, String

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
