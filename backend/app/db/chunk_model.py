from datetime import datetime
from sqlalchemy import DateTime, Column, Integer, String, Text, ForeignKey

from backend.app.db.database import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False)
    character_count = Column(Integer, nullable=False)
    start_word_index = Column(Integer)
    end_word_index = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    # embedding_status = Column(String, default="pending")
    # embedding_model = Column(String, nullable=True)