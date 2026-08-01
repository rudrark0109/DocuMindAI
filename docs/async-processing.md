# Asynchronous Processing

DocuMindAI accepts a validated PDF and returns HTTP 202 after the file,
document row, and worker task ID have been persisted. OCR, extraction, chunking,
and embedding run in a separate Celery worker, so the browser does not hold an
HTTP request open during model work.

## Runtime flow

1. FastAPI streams the PDF to `storage/` and creates a `queued` document row.
2. The API generates and persists the Celery task ID before publishing the job.
3. Redis durably stores the accepted job using append-only persistence.
4. The worker marks the document `processing`, then records `extracting` and
   `indexing` stages as it runs the existing pipeline service.
5. PostgreSQL stores progress, timestamps, errors, retries, and final state.
6. The frontend polls the status endpoint every two seconds and remains usable.

Celery uses late acknowledgement, rejects tasks when a worker process is lost,
and fetches one job at a time. The indexing service atomically replaces a
document's chunks and embeddings, so redelivery does not duplicate vectors.

## API contract

Upload and queue:

```bash
curl -i -F file=@report.pdf http://localhost:8000/documents/upload
```

The response is HTTP 202 and includes `document_id`, `processing_status`,
`processing_stage`, `processing_progress`, and `worker_task_id`.

Poll status:

```bash
curl http://localhost:8000/documents/DOCUMENT_ID/status
```

`job_status` is one of `queued`, `processing`, `completed`, or `failed`.
The response also contains the current stage, percentage progress, error detail,
retry count, worker task ID, and processing timestamps.

Retry a failed job:

```bash
curl -i -X POST http://localhost:8000/documents/DOCUMENT_ID/retry
```

Only failed jobs may be retried. A retry receives a new persisted task ID and
increments `retry_count`; active or completed jobs return HTTP 409.

## Docker operation

Start or rebuild all services:

```bash
docker compose up --build -d
docker compose ps
```

Inspect processing logs:

```bash
docker compose logs -f backend worker redis
```

The stack contains frontend, backend, worker, Redis, and PostgreSQL/pgvector
services. Redis, PostgreSQL, uploaded files, and model caches use persistent
storage. No Podman command or compatibility layer is supported.

## Verification

Run the mixed-PDF integration smoke test:

```bash
docker compose run --rm backend python -m scripts.verify_document_pipeline
```

Run the 51-page non-blocking test:

```bash
docker compose run --rm backend python -m scripts.verify_document_pipeline --scanned-pages 50
```

The verifier measures upload latency separately, polls the job through
completion, checks PostgreSQL vectors, repeats embedding to prove idempotency,
runs semantic search, and cleans up its generated data.

OCR resource defaults are bounded for worker safety: ordinary pages render at
150 DPI, documents over 20 pages use a 96-DPI throughput profile, and every
image has a 2,400-pixel maximum side and 4-million-pixel maximum. Document and
text-line orientation passes are disabled by default on the CPU worker; they can
be enabled through `OCR_USE_DOC_ORIENTATION` and
`OCR_USE_TEXTLINE_ORIENTATION` when higher layout tolerance is more important
than throughput.

Validation on July 27, 2026:

- The two-page mixed-PDF smoke returned from upload in 0.128 seconds and
  completed hybrid OCR, indexing, and search in 24.087 seconds.
- A queued document completed after the worker was stopped and restarted.
- A generated 51-page mixed PDF was accepted without blocking but remained in
  OCR extraction beyond 900 seconds. The large-file completion criterion is
  therefore still open; the verifier now allows a size-aware timeout and never
  cleans up a non-terminal job.

## Current limits

- Progress is stage-based rather than page-by-page.
- One worker process handles one document at a time by default to bound CPU and
  memory use; scale only after measuring OCR memory behavior.
- Manual retry is supported. Automated retry policy and dead-letter monitoring
  remain operational follow-ups.
- Issue #14 separately tracks bounded high-resolution OCR rendering and stale
  processing recovery; this queue implementation does not close that review.
