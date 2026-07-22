# DocuMindAI

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

- Upload and manage PDF documents via API or React frontend
- Store document metadata and processing status in PostgreSQL
- **Extract text from PDFs** using intelligent OCR decision making
- **Chunk extracted text** for semantic search and RAG preparation
- ML-based OCR decision engine with layout-aware feature extraction
- Backend API built with FastAPI
- React + Vite frontend for file upload and response display
- Foundation for embeddings, vector search (`pgvector`), and RAG Q&A

## Detailed Tech Stack

### Backend

- `FastAPI`: API framework for building and serving REST endpoints
- `Uvicorn`: ASGI server used to run the FastAPI application
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
  - Orchestrates the extraction strategy: first checks OCR requirement, then extracts text if possible
  - Handles pending OCR case when extraction requires OCR processing
- **New API Endpoints**:
  - `POST /documents/{document_id}/ocr-verdict` - Get OCR decision for a document
  - `POST /documents/{document_id}/extract` - Extract text from a document
  - `GET /documents/{document_id}/text` - Retrieve extracted text
- **Model Artifacts**:
  - `models/ocr_decision_model.joblib` - Trained Random Forest OCR decision model
  - `models/ocr_model_metadata.json` - Model metadata including feature columns and version

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

### Supporting Work

- Notebook work added for extraction and model exploration:
  - `notebooks/01_extraction_quality_analyzing.ipynb`
  - `notebooks/02_model.ipynb`
  - `notebooks/03_layout_feature_extraction.ipynb`
  - `notebooks/04_train_with_layout_features.ipynb`

## Current State

DocuMindAI now supports a complete document intake and processing pipeline:

- Upload documents through the React frontend or API
- Persist file metadata and processing state in PostgreSQL
- Store uploaded files locally in `storage/`
- Retrieve uploaded documents through the API
- **Intelligently extract text from PDFs** using layout-aware OCR decision making
- **Chunk extracted text** for semantic search and RAG preparation
- Persist document chunks in the database with word-level positioning for retrieval accuracy
- Use the notebook and model assets as the base for OCR and extraction experiments

## Current API

Base URL: `http://127.0.0.1:8000`

### System Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check

### Document Management

- `POST /documents/upload` - Upload a PDF document
- `GET /documents` - List uploaded documents (newest first)
- `GET /documents/{document_id}` - Fetch document metadata by ID

### Document Processing

- `POST /documents/{document_id}/ocr-verdict` - Determine if OCR is needed for the document
- `POST /documents/{document_id}/extract` - Extract text from the document (intelligently uses OCR decision)
- `GET /documents/{document_id}/text` - Retrieve extracted text for a document
- `POST /documents/{document_id}/chunk` - Chunk extracted text and persist chunks

### Interactive Documentation

- `http://127.0.0.1:8000/docs` - Swagger UI (interactive API explorer)

## Document Processing Workflow

The typical workflow for processing a document is:

1. **Upload** → `POST /documents/upload` - Upload a PDF file
2. **Extract** → `POST /documents/{document_id}/extract` - Extract text from the PDF
   - Automatically checks if OCR is needed using the ML model
   - If OCR not needed, extracts text directly using PyMuPDF
   - If OCR needed, returns pending status for future OCR processing
3. **Chunk** → `POST /documents/{document_id}/chunk` - Split extracted text into chunks
   - Creates overlapping chunks for better context retention
   - Persists chunks with word-level positioning for precise retrieval

Alternatively, you can:

- Check OCR requirement first → `POST /documents/{document_id}/ocr-verdict` before extraction
- Retrieve extracted text → `GET /documents/{document_id}/text` after extraction
- List all documents → `GET /documents` to see all uploaded/processed documents

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
|  |  |  `- extraction_pipeline.py        # Orchestrates extraction
|  |  |- indexing/
|  |  |  |- text_chunker.py               # Text chunking logic
|  |  |  `- chunking_pipeline.py          # Chunking orchestration
|  |  |- schemas/                         # Pydantic models
|  |  `- services/                        # File storage, utilities
|  `- main.py                     # FastAPI app entry point
|- frontend/
|  |- src/
|  `- package.json
|- models/
|  |- ocr_decision_model.joblib          # Trained OCR decision model
|  `- ocr_model_metadata.json            # Model metadata
|- notebooks/                            # Jupyter notebooks for experimentation
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

Check status or stop the stack with:

```bash
docker compose ps
docker compose down
```

Database data, uploaded documents, and the downloaded embedding-model cache are
persisted across container restarts. To follow startup logs, run
`docker compose logs -f`.

### Run directly on the host

Use Python 3.12 for the backend and Node.js 22 for the frontend. First create the
local environment file:

```bash
cp .env.example .env
```

Start PostgreSQL and install the backend dependencies:

```bash
docker compose up -d postgres
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then run the backend:

```bash
uvicorn backend.app.main:app --reload
```

In another terminal, run the frontend:

```bash
cd frontend
npm ci
npm run dev
```

Vite runs with host `0.0.0.0` (see frontend scripts).

## Completed Features

- Document upload and metadata management
- OCR decision engine with layout-aware ML model
- PDF text extraction using PyMuPDF
- Intelligent extraction strategy (OCR vs direct extraction)
- Text chunking with configurable overlap
- Chunk persistence and word-level positioning

## Planned Next Steps

- OCR extraction pipeline for documents requiring OCR
- Embedding generation for document chunks
- Vector indexing with `pgvector` for semantic search
- Semantic search endpoints over the document corpus
- RAG chat experience for document Q&A
- Improved document status tracking with queued/processing/completed/failed states
- Batch processing for multiple documents
- Webhook support for async document processing

## Documentation

Project documentation lives in [`docs/DocuMindAI - Project Report.md`](docs/DocuMindAI%20-%20Project%20Report.md). It includes the project abstract, architecture notes, development log, glossary, and appendix.
