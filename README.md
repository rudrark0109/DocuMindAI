# DocuMindAI

Current version: **v1.2.2**

DocuMindAI is an AI-powered document management system for ingesting files, extracting structured information, and preparing data for semantic search and RAG workflows.

## Project Purpose

The purpose of this project is to build an end-to-end document intelligence platform that can:

- Accept user documents in common formats
- Store and manage document metadata reliably
- Extract useful information from documents
- Prepare the data layer needed for semantic search and Retrieval-Augmented Generation (RAG)
- Enable future document Q&A experiences powered by AI

In short, DocuMindAI is being built as the base infrastructure for intelligent document understanding and retrieval.

## Features

- Upload PDFs with an immediate `202 Accepted` response
- Process selective extraction, chunking, and embedding in a durable Celery worker
- Store document metadata, job stage, progress, errors, and retry state in PostgreSQL
- **Extract text from PDFs** using intelligent OCR decision making
- **Chunk extracted text** for semantic search and RAG preparation
- Generate and persist normalized 384-dimensional chunk embeddings
- Search embedded chunks by cosine similarity with source-document references
- ML-based OCR decision engine with layout-aware feature extraction
- PaddleOCR page-extraction service with normalized confidence metadata
- Backend API built with FastAPI
- React + Vite frontend for file upload and response display
- `pgvector` semantic retrieval foundation for future RAG Q&A

## Detailed Tech Stack

### Backend

- `FastAPI`: API framework for building and serving REST endpoints
- `Uvicorn`: ASGI server used to run the FastAPI application
- `Celery`: Durable document-processing worker
- `Redis`: Persistent task broker and worker result backend
- `SQLAlchemy`: ORM for database modeling and queries
- `python-multipart`: Handles file uploads through form-data

### Database and Storage

- `PostgreSQL`: Primary relational database for document metadata
- `psycopg2-binary`: PostgreSQL database driver
- Local file storage (`storage/`): Uploaded files are persisted on disk

### Configuration and Validation

- `Pydantic` + `pydantic-settings`: Settings and structured data validation
- `.env` support (`python-dotenv`): Environment-based configuration for runtime settings such as `DATABASE_URL`

### Document Processing & ML

- `PyMuPDF` (`pymupdf` / `fitz`): PDF text extraction
- `PaddleOCR` + `PaddlePaddle`: OCR inference for scanned PDF pages
- `scikit-learn`: Machine learning for OCR decision making
- `joblib`: Model serialization for the trained OCR decision model
- `pandas`: Data handling and feature engineering for ML models

### Frontend

- `React`: UI layer for document upload flow
- `Vite`: Frontend dev server and build tooling
- JavaScript fetch-based service layer (`frontend/src/services/documentApi.js`) for backend API communication

## Recent Changes

### Phase 1: Core Document Management

- Backend project structure and app bootstrap are set up under `backend/app`
- FastAPI app initialization with root and health endpoints:
  - `GET /`
  - `GET /health`
- Document API module created with `/documents` router
- Upload endpoint implemented:
  - `POST /documents/upload`
  - File type validation for PDF
  - Uploaded file persistence via storage service
  - UUID-based document ID creation and document code assignment
  - Metadata persistence to database with initial status `uploaded`
- Document retrieval endpoints implemented:
  - `GET /documents` (newest-first ordering by `created_at`)
  - `GET /documents/{document_id}` (404 handling when missing)
- SQLAlchemy `Document` model implemented with fields for document tracking and extraction status

### Phase 2: OCR Decision Engine & PDF Text Extraction

- **OCR Decision Engine** (`backend/app/extraction/ocr_decision_engine.py`):
  - Loads a trained Random Forest model to predict if OCR is needed for a PDF
  - Extracts layout and content features from PDFs to inform the decision
  - Returns prediction confidence and probabilities
- **PDF Feature Extraction** (`backend/app/extraction/pdf_feature_extractor.py`):
  - Extracts structural features from PDFs (page count, text density, etc.)
  - Features used by the OCR decision model
- **PDF Text Extraction** (`backend/app/extraction/pdf_extractor.py`):
  - Extracts text from PDFs using PyMuPDF
  - Returns text per page with metadata (character count, word count)
  - Tracks extraction method and success status
- **Extraction Pipeline** (`backend/app/extraction/extraction_pipeline.py`):
  - Routes direct-text PDFs to PyMuPDF and OCR-required PDFs to PaddleOCR
  - Returns a consistent extraction contract for either strategy
- **Asynchronous Upload Orchestration** (`POST /documents/upload`):
  - Persists the uploaded PDF with a `queued` status
  - Queues the existing extraction and indexing pipeline in Celery
  - Returns `202 Accepted` with the document and worker task IDs
  - Persists stage, progress, timestamps, retry count, and failure details
- **New API Endpoints**:
  - `POST /documents/{document_id}/ocr-verdict` - Get OCR decision for a document
  - `POST /documents/{document_id}/extract` - Extract text from a document
  - `GET /documents/{document_id}/text` - Retrieve extracted text
- **Model Artifacts**:
  - `models/ocr_decision_model.joblib` - Trained Random Forest OCR decision model
  - `models/ocr_model_metadata.json` - Model metadata including feature columns and version
  - DocuMindAI consumes these artifacts for inference only. Training data,
    notebooks, retraining, and model rewiring belong to the OCRRouter project.

### Phase 3: Text Chunking Pipeline

- **Text Chunker** (`backend/app/indexing/text_chunker.py`):
  - Splits extracted text into configurable chunks (default: 800 words per chunk, 120-word overlap)
  - Maintains word-level indices for chunk positioning in original text
  - Handles empty/whitespace-only text gracefully
- **Chunking Pipeline** (`backend/app/indexing/chunking_pipeline.py`):
  - Orchestrates chunking for a complete document
  - Validates presence of extracted text before chunking
- **Document Chunk Model** (`backend/app/db/chunk_model.py`):
  - SQLAlchemy model for persisting document chunks
  - Tracks chunk index, text, word/character counts, and word-level positions
  - Foreign key relationship to documents table
- **New API Endpoint**:
  - `POST /documents/{document_id}/chunk` - Chunk extracted text and persist chunks
- **Enhanced Document Model**:
  - New fields: `extracted_text`, `extraction_method`, `ocr_required`, `ocr_confidence`, `ocr_model_version`

## Current State

DocuMindAI now supports a complete document intake and processing pipeline:

- Upload documents through the React frontend or API
- Persist file metadata and processing state in PostgreSQL
- Store uploaded files locally in `storage/`
- Retrieve uploaded documents through the API
- **Intelligently extract text from PDFs** using layout-aware OCR decision making
- **Chunk extracted text** for semantic search and RAG preparation
- Persist document chunks in the database with word-level positioning for retrieval accuracy
- Consume the versioned OCR-routing model artifact through a stable runtime
  interface; training and experimentation live in OCRRouter

## Current API

Base URL: `http://127.0.0.1:8000`

### System Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check

### Document Management

- `POST /documents/upload` - Store a PDF, queue processing, and return `202 Accepted`
- `GET /documents` - List uploaded documents (newest first)
- `GET /documents/{document_id}` - Fetch document metadata by ID
- `GET /documents/{document_id}/status` - Poll processing stage, progress, and errors
- `POST /documents/{document_id}/retry` - Safely requeue a failed document
- `PATCH /documents/{document_id}` - Rename a document
- `DELETE /documents/{document_id}` - Delete a document and its stored file

### Document Processing and Diagnostics

- `POST /documents/{document_id}/ocr-verdict` - Return the persisted OCR decision, or calculate it for a legacy document
- `POST /documents/{document_id}/extract` - Return an existing extraction idempotently, or retry a failed/legacy document
- `GET /documents/{document_id}/text` - Retrieve extracted text for a document
- `POST /documents/{document_id}/chunk` - Chunk extracted text and persist chunks
- `POST /documents/{document_id}/embed` - Embed pending chunks
- `POST /search` - Search embedded chunks, optionally filtered by document

### Interactive Documentation

- `http://127.0.0.1:8000/docs` - Swagger UI (interactive API explorer)

## Document Processing Workflow

The normal client workflow is:

1. **Upload and queue** → `POST /documents/upload`
   - Stores the PDF and creates its document record
   - Returns `202 Accepted` without waiting for OCR or embeddings
2. **Track processing** → `GET /documents/{document_id}/status`
   - Reports queued, active stage, percentage progress, completion, or failure
   - The React client polls this endpoint without blocking the browser
3. **Process in the worker**
   - Automatically checks whether OCR is needed using the ML model
   - Routes each native page to PyMuPDF and OCR-required pages to PaddleOCR
   - Persists extracted text, processing metadata, chunks, and embeddings
   - Uses late task acknowledgement and idempotent indexing for safe redelivery
4. **Read text** → `GET /documents/{document_id}/text` - Retrieve the persisted result
5. **Search** → `POST /search` - Retrieve the most similar passages
   - Accepts `query`, `top_k`, `similarity_threshold`, and optional `document_id`
   - Returns chunk text, preview, cosine similarity, and document references
6. **Chunk** → `POST /documents/{document_id}/chunk` - Split extracted text into chunks
   - Creates overlapping chunks for better context retention
   - Persists chunks with word-level positioning for precise retrieval

The chunk and embed endpoints remain available for diagnostics and legacy
documents. New successful uploads run both stages automatically. Rebuilding an
index replaces the document's existing chunks and vectors atomically.

The decision and extraction POST endpoints remain available for diagnostics,
legacy documents, and retries. Calling extraction again for a successfully
processed document returns the persisted result without running the pipeline a
second time. A request made while extraction is in progress returns HTTP 409.

You can also:

- List all documents → `GET /documents` to see all uploaded/processed documents

Example search request:

```bash
curl -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"invoice payment terms","top_k":5,"similarity_threshold":0.25}'
```

### PaddleOCR service

`backend/app/extraction/paddle_ocr_extractor.py` provides the focused OCR
service used for scanned PDFs. It:

- lazily initializes and caches a CPU-backed PP-OCRv6 engine;
- renders PDF pages individually at a configurable DPI;
- returns document text plus page-level text, line confidence, bounding boxes,
  word counts, and average page confidence;
- keeps downloaded PaddleOCR models in the persistent `paddle_cache` Docker
  volume.

The OCR decision engine and execution service remain separate components. The
extraction pipeline connects them by routing `NO` verdicts to PyMuPDF and `YES`
verdicts to PaddleOCR.

Configuration is available through `PADDLE_OCR_LANGUAGE`,
`PADDLE_OCR_VERSION`, `PADDLE_OCR_DEVICE`, `OCR_RENDER_DPI`,
`OCR_TEXT_SCORE_THRESHOLD`, `OCR_USE_DOC_ORIENTATION`, and
`OCR_USE_TEXTLINE_ORIENTATION`. `OCR_ENABLE_MKLDNN` defaults to `false` for
PP-OCRv6 compatibility with the pinned PaddlePaddle CPU runtime. See
`.env.example` for defaults.

`MAX_UPLOAD_SIZE_MB` limits uploads before processing and defaults to 25 MB.

## Project Structure

```text
DocuMindAI/
|- backend/
|  |- app/
|  |  |- api/
|  |  |  `- documents.py          # Document management endpoints
|  |  |- core/                     # Configuration and settings
|  |  |- db/
|  |  |  |- models.py             # Document model
|  |  |  |- chunk_model.py        # DocumentChunk model
|  |  |  `- database.py           # Database connection
|  |  |- extraction/
|  |  |  |- ocr_decision_engine.py        # ML-based OCR decision
|  |  |  |- pdf_feature_extractor.py      # Feature extraction from PDFs
|  |  |  |- pdf_extractor.py              # Text extraction from PDFs
|  |  |  |- paddle_ocr_extractor.py       # PaddleOCR page extraction service
|  |  |  `- extraction_pipeline.py        # Orchestrates extraction
|  |  |- indexing/
|  |  |  |- text_chunker.py               # Text chunking logic
|  |  |  `- chunking_pipeline.py          # Chunking orchestration
|  |  |- retrieval/
|  |  |  `- vector_search.py              # pgvector cosine retrieval
|  |  |- worker/                           # Celery app and processing task
|  |  |- schemas/                         # Pydantic models
|  |  `- services/                        # File storage, utilities
|  `- main.py                     # FastAPI app entry point
|- frontend/
|  |- src/
|  `- package.json
|- models/
|  |- ocr_decision_model.joblib          # Trained OCR decision model
|  `- ocr_model_metadata.json            # Model metadata
|- storage/                              # Uploaded files storage
|- requirements.txt
`- README.md
```

## Getting Started

### Docker Compose (recommended)

Docker is the only host dependency. Start the complete stack with:

```bash
docker compose up --build -d
```

The services are then available at:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5433`
- Redis and the Celery worker are internal Docker Compose services

Check status or stop the stack with:

```bash
docker compose ps
docker compose down
```

Database data, queued jobs, uploaded documents, and downloaded model caches are
persisted across container restarts. To follow startup logs, run
`docker compose logs -f`.

The backend runs `alembic upgrade head` before starting Uvicorn, so both fresh
and existing Docker volumes are migrated automatically.

Run the retrieval quality and latency sanity check with:

```bash
docker compose run --rm backend python -m scripts.evaluate_retrieval
```

Measured release-readiness results and limitations are recorded in
[`docs/retrieval-evaluation.md`](docs/retrieval-evaluation.md).

### End-to-end pipeline verification

DocuMindAI is configured and supported through Docker Compose. With the stack
running, exercise a real two-page mixed PDF through selective OCR, chunking,
embeddings, PostgreSQL/pgvector, and semantic search:

```bash
docker compose run --rm backend python -m scripts.verify_document_pipeline
```

The command also repeats the embedding endpoint and verifies that it creates
no duplicate vectors, then confirms that a natural-language query retrieves the
uploaded OCR-produced passage. See `docs/pre-search-readiness.md` and
`docs/retrieval-evaluation.md` for recorded results and limitations.

To exercise the non-blocking contract with a generated 51-page mixed PDF (one
native page and 50 image-only pages), run:

```bash
docker compose run --rm backend python -m scripts.verify_document_pipeline --scanned-pages 50
```

The verifier reports upload latency separately from worker processing time and
removes its generated document, stored PDF, chunks, and embeddings afterward.

## Completed Features

- Document upload and metadata management
- OCR decision engine with layout-aware ML model
- PDF text extraction using PyMuPDF
- PaddleOCR service for page rendering and normalized OCR output
- Intelligent extraction strategy (OCR vs direct extraction)
- Text chunking with configurable overlap
- Chunk persistence and word-level positioning
- Automatic chunk embedding with `sentence-transformers/all-MiniLM-L6-v2`
- Atomic replacement of a document's chunks and vectors during re-indexing
- Semantic pgvector search with ranked passages and source references
- Durable Redis/Celery background processing with polling, failure details, and retry
- Non-blocking React upload progress and failed-job retry controls
- User-facing document rename and delete actions

## Planned Next Steps

- Add OCR quality benchmarks and a Tesseract fallback
- RAG chat experience for document Q&A
- PDF/text viewer with synchronized page and search-result highlighting
- Batch processing for multiple documents
- Webhook support for async document processing

## Documentation

Project documentation lives in [`docs/DocuMindAI - Project Report.md`](docs/DocuMindAI%20-%20Project%20Report.md).
The background worker contract and operations are documented in
[`docs/async-processing.md`](docs/async-processing.md), and the outstanding
Notion sequence is mirrored in
[`docs/notion-roadmap-sync.md`](docs/notion-roadmap-sync.md).
