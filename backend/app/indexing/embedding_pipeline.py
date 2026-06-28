from sqlalchemy.orm import Session

from backend.app.indexing.embedding_generator import EMBEDDING_MODEL_NAME, generate_embeddings
from backend.app.db.chunk_model import DocumentChunk

def embed_document_chunks(document_id: str, db: Session) -> dict:
    pending_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id, DocumentChunk.embedding_status == "pending").order_by(DocumentChunk.id.asc()).all()

    if not pending_chunks:
        return {
            "document_id": document_id,
            "embedded_chunk_count": 0,
            "status": "no_pending_chunks",
            "embedding_model": EMBEDDING_MODEL_NAME,
        }
    
    chunk_texts = [chunk.chunk_text for chunk in pending_chunks]

    try:
        vectors = generate_embeddings(chunk_texts)

        for chunk, vector in zip(pending_chunks, vectors):
            chunk.embedding = vector
            chunk.embedding_model = EMBEDDING_MODEL_NAME
            chunk.embedding_status = "embedded"

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "document_id": document_id,
        "embedded_chunk_count": len(pending_chunks),
        "status": "embedded",
        "embedding_model": EMBEDDING_MODEL_NAME,
    }