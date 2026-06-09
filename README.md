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

- Upload and manage documents (`PDF`, `JPEG`, `JPG`, `PNG`)
- Store document metadata and processing status in PostgreSQL
- Backend API built with FastAPI
- React + Vite frontend for file upload and response display
- Foundation for OCR, embeddings, vector search (`pgvector`), and RAG Q&A

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

### Document Processing Foundation

- `PyMuPDF` (`pymupdf` / `fitz`): Included for PDF document extraction workflows

### Frontend

- `React`: UI layer for document upload flow
- `Vite`: Frontend dev server and build tooling
- JavaScript fetch-based service layer (`frontend/src/services/documentApi.js`) for backend API communication

## Recent Changes

The following work has been added to the current codebase:

- Backend project structure and app bootstrap are set up under `backend/app`
- FastAPI app initialization with root and health endpoints:
  - `GET /`
  - `GET /health`
- Document API module created with `/documents` router
- Upload endpoint implemented:
  - `POST /documents/upload`
  - File type validation for PDF/JPEG/JPG/PNG
  - Uploaded file persistence via storage service
  - UUID-based document ID creation and document code assignment
  - Metadata persistence to database with initial status `uploaded`
- Document retrieval endpoints implemented:
  - `GET /documents` (newest-first ordering by `created_at`)
  - `GET /documents/{document_id}` (404 handling when missing)
- SQLAlchemy `Document` model implemented with fields for:
  - IDs/codes
  - original and saved filenames
  - file path and content type
  - file size, creation timestamp, and processing status
- Database session/engine setup completed with configurable `DATABASE_URL`
- Frontend upload page implemented with:
  - File selection
  - Upload button + uploading state
  - Success/error feedback UI
  - Display of returned uploaded file details
- Notebook work added for extraction and model exploration:
  - `notebooks/01_extraction_quality_analyzing.ipynb`
  - `notebooks/02_model.ipynb`
  - `notebooks/03_layout_feature_extraction.ipynb`
  - `notebooks/04_train_with_layout_features.ipynb`
- OCR decision model artifact checked in for layout-aware OCR selection:
  - `models/ocr_decision_rf_layout_v1.joblib`
  - `models/ocr_decision_rf_layout_v1_metadata.json`

## Current State

DocuMindAI now supports the core document intake flow:

- Upload documents through the React frontend
- Persist file metadata and processing state in PostgreSQL
- Store uploaded files locally in `storage/`
- Retrieve uploaded documents through the API
- Use the notebook and model assets as the base for OCR and extraction experiments

## Current API

Base URL: `http://127.0.0.1:8000`

- `GET /` - Welcome message
- `GET /health` - Health check
- `POST /documents/upload` - Upload a document
- `GET /documents` - List uploaded documents (newest first)
- `GET /documents/{document_id}` - Fetch one document by ID

Interactive docs:
- `http://127.0.0.1:8000/docs`

## Project Structure

```text
DocuMindAI/
|- backend/
|  |- app/
|  |  |- api/
|  |  |- core/
|  |  |- db/
|  |  |- extraction/
|  |  |- schemas/
|  |  `- services/
|- frontend/
|  |- src/
|  `- package.json
|- models/
|- notebooks/
|- storage/
|- requirements.txt
`- README.md
```

## Getting Started

### 1. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

The backend reads environment variables from `.env` (project root).  
Set at least:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/documind_ai
```

If `DATABASE_URL` is not set, the app uses the default in `backend/app/core/config.py`.

### 3. Run backend

```bash
uvicorn backend.app.main:app --reload
```

### 4. Run frontend

```bash
cd frontend
npm install
npm run dev
```

Vite runs with host `0.0.0.0` (see frontend scripts).

## Planned Next Steps

- OCR extraction pipeline for uploaded documents
- Layout-aware OCR decisioning and extraction quality scoring
- Embedding generation and vector indexing with `pgvector`
- Semantic search over the document corpus
- RAG chat experience for document Q&A
- Better document status tracking for queued, processed, and failed states

## Documentation

Project documentation lives in [`docs/`](docs/README.md). It includes the project abstract, architecture notes, development log, glossary, and appendix.
