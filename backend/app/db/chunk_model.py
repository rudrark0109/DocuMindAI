from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Column, Integer, String, Text, ForeignKey, UniqueConstraint

from backend.app.db.database import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_index",
        ),
    )
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False)
    character_count = Column(Integer, nullable=False)
    start_word_index = Column(Integer)
    end_word_index = Column(Integer)
    source_page_start = Column(Integer, nullable=True)
    source_page_end = Column(Integer, nullable=True)
    source_location = Column(Text, nullable=True)
    chunker_version = Column(String, nullable=False, default="fixed-window-v1")
    source_format = Column(String, nullable=True)
    heading_path = Column(Text, nullable=True)
    block_types = Column(Text, nullable=True)
    previous_chunk_id = Column(String, nullable=True)
    next_chunk_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    embedding = Column(Vector(384), nullable=True)
    embedding_model = Column(String, nullable=True)
    embedding_status = Column(String, default="pending")
