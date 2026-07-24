from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.db.chunk_model import DocumentChunk
from backend.app.indexing.embedding_generator import (
    EMBEDDING_MODEL_NAME,
    generate_embeddings,
)
from backend.app.indexing.text_chunker import chunk_text


def rebuild_document_index(document, db: Session) -> dict:
    """Atomically replace a document's chunks and embeddings."""
    if not document.extracted_text:
        raise ValueError("Document has no extracted text to index.")

    chunks = chunk_text(document.extracted_text)
    vectors = generate_embeddings([chunk["text"] for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("Embedding count does not match chunk count.")

    try:
        (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document.id)
            .delete(synchronize_session=False)
        )

        for chunk, vector in zip(chunks, vectors):
            db.add(
                DocumentChunk(
                    id=str(uuid4()),
                    document_id=document.id,
                    chunk_index=chunk["chunk_index"],
                    chunk_text=chunk["text"],
                    word_count=chunk["word_count"],
                    character_count=chunk["char_count"],
                    start_word_index=chunk["start_word_index"],
                    end_word_index=chunk["end_word_index"],
                    embedding=vector,
                    embedding_model=EMBEDDING_MODEL_NAME,
                    embedding_status="embedded",
                )
            )

        document.processing_status = "embedded"
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        raise

    return {
        "document_id": document.id,
        "chunk_count": len(chunks),
        "embedded_chunk_count": len(vectors),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "status": "embedded",
    }
