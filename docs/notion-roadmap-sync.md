# DocuMindAI Notion Roadmap Sync

Last synchronized: July 27, 2026 (America/Chicago)

This file is a working copy of the outstanding implementation sequence in the
[DocuMindAI Notion project](https://app.notion.com/p/3a5bab1b6be880e3a15dccd31aa1eb7a).
Notion remains the planning source of truth; this copy keeps the repository and
delivery work aligned.

## Current delivery status

- Semantic retrieval is on `main` at commit `cbe9f0a`; the older roadmap note
  saying PR #13 was closed without integration is obsolete.
- Durable asynchronous processing is implemented on the current working branch:
  upload returns 202, Redis stores accepted jobs, Celery processes them, job
  state is persisted in PostgreSQL, and the frontend polls without blocking.
  Delivery and remaining acceptance work are tracked in
  [GitHub Issue #16](https://github.com/rudrark0109/DocuMindAI/issues/16).
- A Docker smoke test passed both normally and with the worker stopped during
  upload and restarted afterward.
- Issue #14 remains a separate review-gated OCR rendering and stale-processing
  design item. The async queue work does not claim to resolve its bounded
  high-resolution rendering requirement.

## Remaining v2 work

1. Finish the async-processing delivery: review, commit, PR, large scanned-PDF
   load coverage, browser end-to-end coverage, and operational metrics.
2. Complete the interactive workspace: document metadata library, synchronized
   PDF/text viewer, search results that open their source page/chunk, safe
   highlighting, and clear score explanations.
3. Add empty, loading, failure, partial-failure, and no-result component tests.
4. Complete the v1 documentation, final demo, regression, and release tasks.
5. Resolve Issue #14 through the required code-review workflow.

## Deferred v2.3 work

Start only after the v2 queue, retrieval API, and workspace are stable.

1. Multi-format ingestion for PDF, DOCX, TXT, Markdown, CSV, PNG, JPG, and JPEG
   through a normalized block/provenance contract.
2. Deterministic structure-aware chunking that preserves headings, sentences,
   paragraphs, tables, source locations, adjacency, and chunker versions.
3. Retrieval evaluation and tuning against the current fixed-window baseline.
4. Provider-neutral grounded RAG Q&A with structured citations, abstention,
   document-scope isolation, prompt-injection tests, and cost/latency metrics.

## Source plans

- [v2 roadmap](https://app.notion.com/p/3a9bab1b6be881e1a44ef220b7d401c1)
- [v2.3 intelligent knowledge layer](https://app.notion.com/p/3a9bab1b6be881188da7f3063fd16481)
- [multi-format ingestion](https://app.notion.com/p/3a9bab1b6be881be8772f9dde93d202a)
- [structure-aware chunking](https://app.notion.com/p/3a9bab1b6be8818b9dc9efbe2fbe91fb)
- [generative RAG with citations](https://app.notion.com/p/3a9bab1b6be8814fb10fdc03dba7a828)
