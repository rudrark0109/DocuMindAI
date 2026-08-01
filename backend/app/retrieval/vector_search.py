import json
import re

from sqlalchemy.orm import Session

from backend.app.db.chunk_model import DocumentChunk
from backend.app.db.models import Document
from backend.app.indexing.embedding_generator import (
    EMBEDDING_MODEL_NAME,
    generate_embedding,
)

PREVIEW_LENGTH = 240


def _lexical_score(query: str, text: str) -> float:
    query_terms = re.findall(r"[a-z0-9]+", query.lower())
    if not query_terms:
        return 0.0
    text_lower = text.lower()
    text_terms = set(re.findall(r"[a-z0-9]+", text_lower))
    overlap = sum(1 for term in query_terms if term in text_terms) / len(query_terms)
    phrase_bonus = 0.35 if query.strip().lower() in text_lower else 0.0
    return min(1.0, overlap * 0.65 + phrase_bonus)


def search_document_chunks(
    query: str,
    db: Session,
    *,
    top_k: int = 5,
    similarity_threshold: float = 0.0,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    max_chunks_per_document: int | None = None,
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
    elif document_ids:
        statement = statement.filter(DocumentChunk.document_id.in_(document_ids))

    candidate_limit = max(top_k * 5, top_k * (max_chunks_per_document or 1))
    rows = (
        statement.filter(distance <= 2.0)
        .order_by(distance.asc())
        .limit(candidate_limit)
        .all()
    )

    candidates = []
    for chunk, document, row_distance in rows:
        semantic_score = 1.0 - float(row_distance)
        lexical_score = _lexical_score(query, chunk.chunk_text)
        combined_score = semantic_score * 0.7 + lexical_score * 0.3
        if combined_score >= similarity_threshold:
            candidates.append((combined_score, semantic_score, lexical_score, chunk, document))
    candidates.sort(key=lambda item: item[0], reverse=True)

    results = []
    document_counts: dict[str, int] = {}
    for combined_score, semantic_score, lexical_score, chunk, document in candidates:
        count = document_counts.get(document.id, 0)
        if max_chunks_per_document is not None and count >= max_chunks_per_document:
            continue
        document_counts[document.id] = count + 1
        source_location = getattr(chunk, "source_location", None)
        try:
            source_location = json.loads(source_location) if source_location else None
        except (TypeError, json.JSONDecodeError):
            source_location = None
        results.append(
            {
            "document_id": document.id,
            "document_code": document.document_code,
            "original_filename": document.original_filename,
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "text": chunk.chunk_text,
            "preview": chunk.chunk_text[:PREVIEW_LENGTH],
            "similarity": round(semantic_score, 6),
            "semantic_score": round(semantic_score, 6),
            "lexical_score": round(lexical_score, 6),
            "combined_score": round(combined_score, 6),
            "source_page_start": getattr(chunk, "source_page_start", None),
            "source_page_end": getattr(chunk, "source_page_end", None),
            "source_location": source_location,
            "chunker_version": getattr(chunk, "chunker_version", "fixed-window-v1"),
            }
        )
        if len(results) >= top_k:
            break
    return results
