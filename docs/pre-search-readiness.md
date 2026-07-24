# Pre-search readiness validation

Validated on Fedora 44 with Docker Engine 29.6.2 and Docker Compose 5.3.1 on
July 24, 2026.

## Automated regression result

```text
27 passed
```

The suite includes a generated, real two-page PDF fixture containing one native
text page and one rasterized image-only page. It verifies:

- the trained OCR decision model returns `NO` for the native page and `YES` for
  the scanned page;
- PaddleOCR rendering runs only for the selected page;
- native and OCR text retain page order without duplicated weak native text;
- indexing replaces chunks and vectors atomically;
- upload limits, partial-file cleanup, failure states, and repeat behavior.

## Live Docker smoke result

Command:

```bash
python scripts/verify_pre_search_pipeline.py
```

Recorded result:

```text
PASS: document=b087eac8-2513-4b6d-9672-eb553bb5fe96 method=hybrid chunks=1 dimensions=384 repeat_embed=no_pending_chunks
```

This verifies the live path:

```text
upload → page-level native/OCR extraction → normalized text → chunk → embedding
```

The extracted scan contained the expected `quarterly revenue` phrase. Direct
PostgreSQL inspection confirmed every embedded chunk had exactly 384 vector
dimensions. Repeating the embedding endpoint returned `no_pending_chunks`.

## Migration and fresh-setup result

The existing persistent database upgraded to Alembic revision `20260724_01`
and gained the `uq_document_chunks_document_index` constraint.

A separate temporary Compose project was then started with a brand-new database
volume. Backend startup automatically:

1. enabled pgvector;
2. applied revision `20260724_01`;
3. created `documents` and `document_chunks`;
4. started successfully with `GET /health` returning `{"status":"healthy"}`.

The temporary validation volumes were removed after the check. The normal
project stack and its original data volume were restored.

## Limitations

- The mixed-PDF regression set is deliberately small and synthetic. It proves
  routing and pipeline correctness, not OCR quality across arbitrary layouts.
- The first cold OCR or embedding request downloads model assets and is slower
  than warm requests; Docker volumes persist both caches.
- OCR routing accuracy is still bounded by the small training/holdout dataset
  documented with the model artifacts.
- Processing is synchronous and best suited to the current PDF-only MVP; a job
  queue remains appropriate for larger production workloads.
