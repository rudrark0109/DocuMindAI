# DocuMindAI

DocuMindAI is an AI-powered document management system designed to ingest files, extract meaning, and enable intelligent retrieval using semantic search and retrieval-augmented generation (RAG).

## What It Does

- Upload and manage documents (PDF, JPEG, JPG, PNG)
- Store document metadata and processing state in PostgreSQL
- Prepare a foundation for OCR, embeddings, and vector search with `pgvector`
- Support downstream RAG workflows for context-aware document Q&A

## Current Backend API

The backend exposes document endpoints under `/documents`:

- `POST /documents/upload`: upload a document file
- `GET /documents`: list all uploaded documents (newest first)
- `GET /documents/{document_id}`: fetch a document by ID

## Tech Stack

- Backend: FastAPI, SQLAlchemy
- Database: PostgreSQL (`psycopg2-binary`)
- Validation/Config: Pydantic, `pydantic_settings`
- Server runtime: Uvicorn

## Project Structure

```text
DocuMindAI/
├── backend/
│   └── app/
│       ├── api/
│       ├── db/
│       ├── schemas/
│       └── services/
├── frontend/
├── storage/
├── requirements.txt
└── README.md
```

## Getting Started

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure database

Set up a PostgreSQL database and configure your backend environment variables (for example, database URL/credentials) as required by your `backend/app/db` configuration.

### 3. Run the API server

```bash
uvicorn backend.app.main:app --reload
```

### 4. Open API docs

After startup, visit:

- `http://127.0.0.1:8000/docs`

## Roadmap

- OCR extraction pipeline for uploaded documents
- Embedding generation and vector indexing with `pgvector`
- Semantic search and RAG chat over document corpus
