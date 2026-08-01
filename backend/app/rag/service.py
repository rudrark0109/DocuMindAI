from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.models import Document
from backend.app.rag.providers import ProviderAnswer, configured_provider
from backend.app.retrieval.vector_search import search_document_chunks


class RAGDocumentNotFound(LookupError):
    pass


def _citation(item: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "citation_id": f"C{index}",
        "document_id": item["document_id"],
        "document_code": item["document_code"],
        "filename": item["original_filename"],
        "chunk_id": item["chunk_id"],
        "chunk_index": item["chunk_index"],
        "text": item["text"],
        "preview": item["preview"],
        "similarity": item["similarity"],
        "semantic_score": item.get("semantic_score"),
        "lexical_score": item.get("lexical_score"),
        "combined_score": item.get("combined_score"),
        "source_page_start": item.get("source_page_start"),
        "source_page_end": item.get("source_page_end"),
        "source_location": item.get("source_location"),
        "chunker_version": item.get("chunker_version"),
    }


def _validate_scope(db: Session, document_id: str | None, document_ids: list[str] | None) -> None:
    ids = [document_id] if document_id else (document_ids or [])
    if not ids:
        return
    existing = {
        row[0]
        for row in db.query(Document.id).filter(Document.id.in_(ids)).all()
    }
    missing = [value for value in ids if value not in existing]
    if missing:
        raise RAGDocumentNotFound(f"Document scope not found: {', '.join(missing)}")


def _bounded_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    remaining = settings.rag_max_context_chars
    bounded = []
    for item in evidence:
        if remaining <= 0:
            break
        copy = dict(item)
        copy["text"] = item["text"][:remaining]
        bounded.append(copy)
        remaining -= len(copy["text"])
    return bounded


def answer_question(
    question: str,
    db: Session,
    *,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    top_k: int = 5,
    similarity_threshold: float | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    _validate_scope(db, document_id, document_ids)
    threshold = (
        settings.rag_similarity_threshold
        if similarity_threshold is None
        else similarity_threshold
    )
    results = search_document_chunks(
        question,
        db,
        top_k=min(top_k, settings.rag_max_citations),
        similarity_threshold=threshold,
        document_id=document_id,
        document_ids=document_ids,
        max_chunks_per_document=2 if document_id is None else None,
    )
    evidence = [_citation(item, index) for index, item in enumerate(results, start=1)]
    if not evidence:
        return {
            "question": question,
            "scope": "document" if document_id else "collection",
            "document_id": document_id,
            "answer": "The available documents do not contain enough evidence to answer that question.",
            "insufficient_evidence": True,
            "citations": [],
            "supporting_excerpts": [],
            "provider": "none",
            "model": None,
            "retrieval_count": 0,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    provider = configured_provider()
    generated: ProviderAnswer = provider.generate(question, _bounded_evidence(evidence))
    known = {item["citation_id"]: item for item in evidence}
    valid_ids = [value for value in generated.citation_ids if value in known]
    invalid_ids = set(generated.citation_ids) - set(valid_ids)
    insufficient = generated.abstain or not generated.answer or not valid_ids or bool(invalid_ids)
    answer = generated.answer
    if insufficient:
        answer = "The available documents do not contain enough verified evidence to answer that question."
        valid_ids = []
    citations = [known[value] for value in valid_ids]
    return {
        "question": question,
        "scope": "document" if document_id else "collection",
        "document_id": document_id,
        "answer": answer,
        "insufficient_evidence": insufficient,
        "citations": citations,
        "supporting_excerpts": [item["preview"] for item in citations],
        "provider": generated.provider,
        "model": generated.model,
        "retrieval_count": len(results),
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
    }
