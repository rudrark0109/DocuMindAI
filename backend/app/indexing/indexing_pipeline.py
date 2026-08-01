import json
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.db.chunk_model import DocumentChunk
from backend.app.indexing.embedding_generator import (
    EMBEDDING_MODEL_NAME,
    generate_embeddings,
)
from backend.app.indexing.text_chunker import STRUCTURE_CHUNKER_VERSION, chunk_blocks, chunk_text


CHUNKER_VERSION = STRUCTURE_CHUNKER_VERSION


def _page_ranges(document) -> list[tuple[int, int, int]]:
    try:
        pages = json.loads(getattr(document, "extracted_pages", None) or "[]")
    except (TypeError, json.JSONDecodeError):
        return []

    ranges = []
    cursor = 0
    for page in pages:
        word_count = len((page.get("text") or "").split())
        if word_count:
            ranges.append((page.get("page_number", len(ranges) + 1), cursor, cursor + word_count))
        cursor += word_count
    return ranges


def _source_pages(chunk: dict, page_ranges: list[tuple[int, int, int]]) -> tuple[int | None, int | None]:
    overlapping = [
        page_number
        for page_number, page_start, page_end in page_ranges
        if chunk["start_word_index"] < page_end and chunk["end_word_index"] > page_start
    ]
    if not overlapping:
        return None, None
    return min(overlapping), max(overlapping)


def rebuild_document_index(document, db: Session) -> dict:
    """Atomically replace a document's chunks and embeddings."""
    if not document.extracted_text:
        raise ValueError("Document has no extracted text to index.")

    try:
        blocks = json.loads(getattr(document, "normalized_blocks", None) or "[]")
    except (TypeError, json.JSONDecodeError):
        blocks = []
    chunks = chunk_blocks(blocks) if blocks else chunk_text(document.extracted_text)
    active_chunker = CHUNKER_VERSION if blocks else "fixed-window-v1"
    page_ranges = _page_ranges(document)
    vectors = generate_embeddings([chunk["text"] for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("Embedding count does not match chunk count.")

    try:
        (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document.id)
            .delete(synchronize_session=False)
        )

        chunk_ids = [str(uuid4()) for _ in chunks]
        for position, (chunk, vector) in enumerate(zip(chunks, vectors)):
            page_start, page_end = _source_pages(chunk, page_ranges)
            structured_location = chunk.get("source_location")
            source_location = json.dumps(structured_location) if structured_location else (
                json.dumps({"page_start": page_start, "page_end": page_end})
                if page_start is not None
                else None
            )
            db.add(
                DocumentChunk(
                    id=chunk_ids[position],
                    document_id=document.id,
                    chunk_index=chunk["chunk_index"],
                    chunk_text=chunk["text"],
                    word_count=chunk["word_count"],
                    character_count=chunk["char_count"],
                    start_word_index=chunk["start_word_index"],
                    end_word_index=chunk["end_word_index"],
                    source_page_start=page_start,
                    source_page_end=page_end,
                    source_location=source_location,
                    chunker_version=active_chunker,
                    source_format=getattr(document, "source_format", None),
                    heading_path=json.dumps(chunk.get("heading_path", [])),
                    block_types=json.dumps(chunk.get("block_types", [])),
                    previous_chunk_id=chunk_ids[position - 1] if position else None,
                    next_chunk_id=chunk_ids[position + 1] if position + 1 < len(chunk_ids) else None,
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
