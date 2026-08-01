from __future__ import annotations

import json
from statistics import mean
from time import perf_counter
from uuid import uuid4

from backend.app.db.chunk_model import DocumentChunk
from backend.app.db.database import SessionLocal
from backend.app.db.models import Document
from backend.app.indexing.embedding_generator import (
    EMBEDDING_MODEL_NAME,
    generate_embeddings,
)
from backend.app.retrieval.vector_search import search_document_chunks

FIXTURE_PREFIX = "EVAL-"
FIXTURES = [
    (
        "solar-energy.pdf",
        "Solar photovoltaic panels convert sunlight into electricity. "
        "An inverter changes direct current into alternating current for a home.",
    ),
    (
        "sourdough-guide.pdf",
        "A sourdough starter is a fermented mixture of flour and water. "
        "Regular feeding keeps the wild yeast active for baking bread.",
    ),
    (
        "postgres-search.pdf",
        "PostgreSQL can store vector embeddings with the pgvector extension. "
        "Cosine distance supports semantic nearest-neighbor retrieval.",
    ),
]
QUERIES = [
    ("How do panels produce power?", "solar-energy.pdf"),
    ("What keeps wild yeast ready for bread?", "sourdough-guide.pdf"),
    ("Which database extension stores embeddings?", "postgres-search.pdf"),
]


def main() -> None:
    db = SessionLocal()
    documents: list[Document] = []
    try:
        vectors = generate_embeddings([text for _, text in FIXTURES])
        pending_chunks = []
        for index, ((filename, text), vector) in enumerate(zip(FIXTURES, vectors)):
            document = Document(
                id=str(uuid4()),
                document_code=f"{FIXTURE_PREFIX}{uuid4().hex[:10].upper()}",
                original_filename=filename,
                saved_filename=filename,
                file_path=f"/tmp/{filename}",
                content_type="application/pdf",
                file_size=len(text.encode()),
                processing_status="embedded",
                extracted_text=text,
                extraction_method="evaluation_fixture",
            )
            documents.append(document)
            db.add(document)
            pending_chunks.append(
                DocumentChunk(
                    id=str(uuid4()),
                    document_id=document.id,
                    chunk_index=index,
                    chunk_text=text,
                    word_count=len(text.split()),
                    character_count=len(text),
                    start_word_index=0,
                    end_word_index=len(text.split()) - 1,
                    embedding=vector,
                    embedding_model=EMBEDDING_MODEL_NAME,
                    embedding_status="embedded",
                )
            )
        db.flush()
        db.add_all(pending_chunks)
        db.commit()

        measurements = []
        for query, expected_filename in QUERIES:
            started = perf_counter()
            results = search_document_chunks(
                query,
                db,
                top_k=3,
                similarity_threshold=0.0,
            )
            latency_ms = (perf_counter() - started) * 1000
            top_result = results[0] if results else None
            measurements.append(
                {
                    "query": query,
                    "expected": expected_filename,
                    "top_result": (
                        top_result["original_filename"] if top_result else None
                    ),
                    "top_similarity": (
                        top_result["similarity"] if top_result else None
                    ),
                    "latency_ms": round(latency_ms, 2),
                    "passed": bool(
                        top_result
                        and top_result["original_filename"] == expected_filename
                    ),
                }
            )

        payload = {
            "fixture_count": len(FIXTURES),
            "query_count": len(QUERIES),
            "top_1_accuracy": (
                sum(item["passed"] for item in measurements) / len(measurements)
            ),
            "mean_warm_query_latency_ms": round(
                mean(item["latency_ms"] for item in measurements),
                2,
            ),
            "embedding_model": EMBEDDING_MODEL_NAME,
            "measurements": measurements,
            "limitations": [
                "The fixture set contains only three short, clearly separated topics.",
                "Latency is measured locally in Docker after the model is loaded.",
                "This sanity check is not a production relevance benchmark.",
            ],
        }
        print(json.dumps(payload, indent=2))
    finally:
        db.rollback()
        document_ids = [document.id for document in documents]
        if document_ids:
            (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id.in_(document_ids))
                .delete(synchronize_session=False)
            )
            (
                db.query(Document)
                .filter(Document.id.in_(document_ids))
                .delete(synchronize_session=False)
            )
            db.commit()
        db.close()


if __name__ == "__main__":
    main()
