from sqlalchemy.orm import Session

from backend.app.db.chunk_model import DocumentChunk
from backend.app.db.models import Document
from backend.app.indexing.embedding_generator import (
    EMBEDDING_MODEL_NAME,
    generate_embedding,
)

PREVIEW_LENGTH = 240


def search_document_chunks(
    query: str,
    db: Session,
    *,
    top_k: int = 5,
    similarity_threshold: float = 0.0,
    document_id: str | None = None,
) -> list[dict]:
    """Return the closest embedded chunks using pgvector cosine distance."""
    query_vector = generate_embedding(query)
    distance = DocumentChunk.embedding.cosine_distance(query_vector)

    statement = (
        db.query(DocumentChunk, Document, distance.label("distance"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(
            DocumentChunk.embedding.is_not(None),
            DocumentChunk.embedding_status == "embedded",
        )
    )
    if document_id is not None:
        statement = statement.filter(DocumentChunk.document_id == document_id)

    maximum_distance = 1.0 - similarity_threshold
    rows = (
        statement.filter(distance <= maximum_distance)
        .order_by(distance.asc())
        .limit(top_k)
        .all()
    )

    return [
        {
            "document_id": document.id,
            "document_code": document.document_code,
            "original_filename": document.original_filename,
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "text": chunk.chunk_text,
            "preview": chunk.chunk_text[:PREVIEW_LENGTH],
            "similarity": round(1.0 - float(row_distance), 6),
        }
        for chunk, document, row_distance in rows
    ]
