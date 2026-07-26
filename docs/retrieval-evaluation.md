# Semantic Retrieval Evaluation

Evaluation date: July 26, 2026  
Scheduled milestone: July 27, 2026

## Scope

This is a release-readiness sanity check for the PDF-only MVP. It verifies that
normalized query embeddings can retrieve stored pgvector chunks, rank the
expected source first, and return document references within reasonable local
latency.

Run it strictly through Docker:

```bash
docker compose run --rm backend python -m scripts.evaluate_retrieval
```

The script creates three temporary documents and chunks, evaluates three
natural-language queries, prints JSON results, and removes its fixtures.

## Results

| Query | Expected top result | Similarity | Latency |
| --- | --- | ---: | ---: |
| How do panels produce power? | `solar-energy.pdf` | 0.611204 | 56.46 ms |
| What keeps wild yeast ready for bread? | `sourdough-guide.pdf` | 0.578947 | 42.99 ms |
| Which database extension stores embeddings? | `postgres-search.pdf` | 0.497727 | 32.25 ms |

- Top-1 accuracy: **3/3 (100%)**
- Mean warm query latency: **43.90 ms**
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Similarity: `1 - cosine_distance`; higher values are more similar

A live `POST /search` request against the existing mixed-PDF smoke document
also returned its persisted chunk with document ID, document code, filename,
chunk metadata, text/preview, and similarity.

## Interpretation and limitations

These results demonstrate that the storage-to-retrieval path works, but they do
not establish production retrieval quality:

- The evaluation has only three short, deliberately distinct topics.
- Latency was measured locally in Docker after the embedding model was loaded.
- Cold model download/startup time, concurrency, large corpora, and approximate
  indexes are not measured.
- No multilingual, adversarial, ambiguous, long-document, or OCR-noise corpus
  is included.
- Similarity thresholds are domain-dependent. The API defaults to `0.0`; clients
  should tune the threshold with representative documents.

The next meaningful quality step is a larger labelled query-to-passage set
drawn from real user documents, with recall@k, mean reciprocal rank, p95
latency, and false-positive analysis.
