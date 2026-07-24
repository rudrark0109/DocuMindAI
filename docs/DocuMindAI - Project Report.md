# DocuMindAI - Project Report

## Abstract

DocuMindAI is a document intelligence platform for ingesting PDFs, images, scans, and business or personal records, then routing them through a deliberate extraction and retrieval pipeline.

The project is designed to show practical AI engineering rather than a stitched-together demo stack. The system stores original files, extracts text when possible, decides when OCR is actually needed, analyzes extraction quality, prepares metadata, generates embeddings, and supports semantic retrieval and future RAG workflows with citations.

The core architectural idea is selective intelligence: do not OCR everything, do not trust every extraction equally, and do not treat retrieval as a generic chatbot wrapper.

## Introduction

DocuMind AI is a smart document management and semantic retrieval system.

The platform is intended to support:

- PDFs
- scanned documents
- images
- government forms
- tax forms
- invoices
- certificates
- academic papers
- resumes
- personal records

The project exists as a long-term AI engineering portfolio piece. Its purpose is to demonstrate system design, retrieval engineering, OCR routing, backend architecture, and maintainable pipeline ownership.

## Design Principle

The project intentionally avoids a generic pattern such as `PDF -> LangChain -> Vector DB -> ChatGPT`.

Instead, the system is being built with explicit control over:

- file ingestion
- extraction quality analysis
- OCR decisioning
- layout-aware processing
- metadata creation
- embedding generation
- retrieval ranking
- citation-ready output

## Project Scope

### In Scope

- Store original uploaded files locally at first, with S3 planned later.
- Store document metadata in PostgreSQL.
- Extract text from PDFs and images.
- Determine whether OCR is needed before OCR is run.
- Analyze extraction quality when text is available.
- Reconstruct or flag layout-heavy documents when needed.
- Generate embeddings for downstream retrieval.
- Support semantic search and retrieval-augmented generation.

### Out of Scope For Now

- Full enterprise workflow automation
- Distributed worker orchestration
- Multi-tenant authorization
- Cloud file storage migration
- Advanced citation UI

### Architectural Constraint

External libraries are acceptable for low-level tasks such as PDF parsing, OCR, and embeddings, but the routing logic and pipeline design should remain custom and explainable.

## System Overview

### Current Stack

- Backend: Python, FastAPI
- Frontend: React, Vite
- Database: PostgreSQL
- Vector storage: pgvector planned
- PDF processing: PyMuPDF, optional pdfplumber
- OCR: PaddleOCR with Tesseract fallback
- Embeddings: sentence-transformers
- Deployment: Docker Compose
- Storage: local filesystem first, S3 later

### Current Backend Shape

The backend follows a clear application layout:

- `api/`
- `core/`
- `db/`
- `schemas/`
- `services/`

The design goal is to keep responsibilities separated so the document pipeline can evolve without tangling API, storage, and extraction logic together.

## Architecture

### Core Flow

1. Upload file
2. Validate file type
3. Generate custom document code
4. Store file on disk
5. Persist metadata in PostgreSQL
6. Extract text
7. Decide whether OCR is needed
8. Run selective OCR if required
9. Analyze extraction or layout quality
10. Generate metadata and embeddings
11. Store vectors and metadata
12. Retrieve with ranking and citations

### Why This Architecture

The architecture is intentionally explicit so each subsystem can be tested and improved independently.

- File storage is separate from metadata storage.
- OCR decisioning is separate from OCR execution.
- Extraction quality is separate from layout understanding.
- Retrieval is separate from ingestion.

That separation keeps the project production-minded and avoids a single monolithic pipeline that is hard to reason about.

### Current Implementation

### Implemented Backend Features

- FastAPI backend is operational
- Document upload and management
  - `POST /documents/upload` - Upload and automatically extract PDF documents
  - `GET /documents` - List all documents
  - `GET /documents/{document_id}` - Retrieve document metadata
- OCR decision engine
  - `POST /documents/{document_id}/ocr-verdict` - Get OCR prediction
  - ML-based decision with confidence scores
- Text extraction pipeline
  - `POST /documents/{document_id}/extract` - Extract text intelligently
  - `GET /documents/{document_id}/text` - Retrieve extracted text
  - Handles both OCR-required and direct extraction paths
- Text chunking pipeline
  - `POST /documents/{document_id}/chunk` - Chunk extracted text
  - Configurable chunk size and overlap
  - Word-level positioning for retrieval accuracy

### Upload Pipeline

The current upload pipeline performs the following steps:

1. Validate the file type (PDF only)
2. Generate a custom document code
3. Store the file locally
4. Store metadata in PostgreSQL with a `processing` status
5. Run the OCR Decision Engine
6. Route native PDFs to PyMuPDF or scanned PDFs to PaddleOCR
7. Persist the extracted text, routing metadata, and final status
8. Return the document ID and complete extraction summary

Clients no longer need to call the OCR-decision and extraction endpoints after
upload. Those endpoints remain available for diagnostics, legacy records, and
safe retries. Completed documents are returned idempotently instead of being
processed twice, while concurrent extraction attempts receive HTTP 409.

### Extraction Pipeline

The extraction pipeline implements intelligent text extraction:

1. Validate document exists and is accessible
2. Run OCR Decision Engine to predict OCR requirement
3. If OCR not needed: extract text directly using PyMuPDF
4. If OCR is needed: render each page and extract text with PaddleOCR
5. Store extraction result, method, and OCR verdict in database
6. Return extraction status and metadata

### Chunking Pipeline

The chunking pipeline breaks extracted text into semantic chunks:

1. Validate document has extracted text
2. Check if document already has chunks (prevents re-chunking)
3. Split text into configurable chunks (default: 800 words, 120-word overlap)
4. Maintain word-level indices for positioning
5. Persist each chunk with metadata (index, word count, character count, positions)
6. Return chunk count and summary

### Database Metadata

The database stores metadata and processing state, including:

**Document Table:**

- internal UUID
- document code (human-readable identifier)
- original filename
- saved filename
- file path
- content type (MIME type)
- file size in bytes
- processing status (uploaded, ocr_checked, text_extracted, text_chunked, etc.)
- created timestamp
- OCR verdict (YES/NO) and confidence score
- OCR model version used
- extracted text
- extraction method (pymupdf, ocr, etc.)

**Document Chunk Table:**

- chunk UUID
- foreign key to document
- chunk index (position in sequence)
- chunk text
- word count and character count
- start and end word indices (for retrieval positioning)
- created timestamp

The document files themselves stay on the filesystem in `storage/`.

## OCR Decision Engine

### Purpose

The OCR Decision Engine determines whether OCR is needed before OCR is performed.

This is a key differentiator in the project because many systems either OCR everything or skip OCR entirely. DocuMind AI routes documents based on evidence.

### Why It Matters

- OCR is expensive.
- Many PDFs already contain usable digital text.
- Running OCR unnecessarily wastes time and compute.
- Selective OCR improves throughput and makes the pipeline more intelligent.

### Current Implementation

The OCR Decision Engine is **now implemented and operational**:
**Components:**

- **Feature Extractor** (`pdf_feature_extractor.py`): Extracts layout and content features from PDFs
  - Page count
  - Text density per page
  - Character and word counts
  - Layout complexity metrics
- **ML Model** (`ocr_decision_engine.py`): Trained Random Forest model
  - Loads serialized model from `models/ocr_decision_model.joblib`
  - Returns binary prediction (YES/NO) and confidence scores
  - Provides per-class probabilities for decision transparency
- **API Endpoint**: `POST /documents/{document_id}/ocr-verdict`
  - Returns OCR requirement prediction with confidence
  - Stored in document metadata for retrieval

**Model Details:**

- Algorithm: Random Forest (scikit-learn)
- Features: Layout-aware extracted from PDF structure
- Output: Binary classification (OCR required: YES/NO)
- Confidence: Probability score for the predicted class
- Model version tracking for traceability

### Dataset Notes

The model was trained on a labeled dataset that includes:

- digital PDFs
- scanned PDFs
- mixed-content PDFs
- academic papers
- forms
- blank pages
- image-heavy pages

Labels are:

- `YES` = OCR required
- `NO` = OCR not required

### Current Result Snapshot

The trained model shows strong performance on the evaluation set. The feature
engineering prioritizes layout characteristics to make robust decisions about
document extractability. The reproducible runtime artifacts are stored under
`models/`, with current limitations recorded in the project documentation.

## Completed Work

### Text Extraction Pipeline

The text extraction pipeline is now operational:
- PDF text extraction using PyMuPDF
- OCR decision engine integration
- Intelligent routing based on document characteristics
- Extraction result persistence and tracking

### Text Chunking Pipeline

Text chunking with word-level positioning is now implemented:
- Configurable chunk size and overlap
- Semantic chunk boundaries
- Word-level indices for precise retrieval
- Database persistence with chunk metadata

### OCR Decision Engine

A trained ML model now makes intelligent OCR decisions:
- Layout-aware feature extraction
- Random Forest classification
- Confidence scoring and transparency
- Model versioning and tracking

## Future Work

### Extraction Quality Analyzer

OCR is not the only quality issue. A document can contain extractable text and still be unusable because:

- text order is broken
- sections are missing
- extraction is corrupted
- the output is unreadable

Planned output classes include:

- `GOOD_TEXT`
- `WEAK_TEXT`
- `CORRUPTED_TEXT`
- `SCANNED_IMAGE`
- `MIXED_CONTENT`

### Layout and Form Understanding

Some documents require structure-aware handling even when text extraction succeeds.

Examples:

- IRS forms
- USCIS forms
- invoices
- bank statements
- academic papers

Planned output classes include:

- `plain_text_ok`
- `needs_layout_reconstruction`
- `needs_table_extraction`
- `needs_form_field_extraction`
- `hybrid_required`

### OCR Extraction

Implemented for documents where OCR is required:

- CPU-backed PaddleOCR integration with cached PP-OCRv6 models
- Configurable PDF page rendering and orientation handling
- Normalized page text, line confidence scores, and bounding boxes
- Extracted text, method, OCR verdict, and processing-status persistence

Planned enhancements:

- Tesseract fallback
- Advanced layout reconstruction
- OCR quality benchmarking

### Embedding and Vector Search

Next phase for semantic capabilities:

- Embedding generation for document chunks
- Vector storage with pgvector
- Semantic search implementation
- Similarity ranking and retrieval

### Downstream Goals

- semantic search
- RAG with citations
- Batch document processing
- Async job queue for large pipelines

## Development Log

This file records meaningful implementation milestones and decisions.

### 2026-06-27

**Text Extraction and Chunking Pipeline Complete**

What changed:

- Implemented PDF text extraction pipeline using PyMuPDF
- Integrated OCR decision engine into extraction flow
- Implemented text chunking with configurable overlap
- Added DocumentChunk model and persistence layer
- Added five new API endpoints for extraction and chunking workflow

Why it changed:

- Extracted text is the foundation for embedding generation and semantic search
- Chunking with word-level positioning ensures precise retrieval context
- Early completion enables faster iteration on downstream features

Implementation details:

- `backend/app/extraction/` module handles OCR decisions and text extraction
- `backend/app/indexing/` module handles text chunking
- `backend/app/db/chunk_model.py` stores chunks with positioning metadata
- API endpoints follow explicit document processing flow

Notes:

- Chunking uses word-level splitting rather than character or sentence boundaries for more flexible downstream processing
- OCR-required documents are processed page-by-page with PaddleOCR
- Chunk overlap (120 words default) balances context preservation with storage efficiency

### 2026-06-19

**OCR Decision Engine and PDF Feature Extraction**

What changed:

- Completed feature engineering for layout-aware OCR decisions
- Trained Random Forest model for OCR requirement prediction
- Added `pdf_feature_extractor.py` for feature generation
- Added `ocr_decision_engine.py` API integration
- Model and metadata artifacts checked into `models/`

Why it changed:

- Selective OCR is a core project principle: avoid unnecessary expensive processing
- Layout features provide better signal than simple heuristics
- ML-based approach enables future refinement with more labeled data

### 2026-06-09

- Established the current FastAPI document intake flow.
- Added local file storage for uploads.
- Persisted document metadata in PostgreSQL.
- Introduced a custom document code for operational tracing.
- Trained and evaluated the OCR decision model with layout-aware features.
- Identified the need for a dedicated extraction quality analyzer and a layout quality analyzer.
- Created the documentation structure to keep project notes, architecture, and progress organized.

### Log Format For Future Entries

- Date
- What changed
- Why it changed
- Notes or risks

## Glossary

- **Document code**: Human-readable operational identifier such as `PDF_A7K92X_20260525_194455`.
- **OCR**: Optical Character Recognition, used to convert image-based document content into text.
- **Extraction quality**: A measure of whether extracted text is usable, complete, and ordered correctly.
- **Layout quality**: A measure of whether the structure of the document is preserved after extraction.
- **Selective OCR**: Running OCR only when the document characteristics indicate it is needed.
- **Embedding**: A vector representation of text used for semantic retrieval.
- **Vector storage**: Database-backed storage for embeddings and similarity search.
- **RAG**: Retrieval-Augmented Generation, where retrieved context is supplied to a generative model.
- **Metadata**: Operational data about a document, such as filename, status, and storage path.

## Appendix

### Current Repository Areas

- `backend/app/` - Main application code
  - `api/` - API route handlers
  - `db/` - Database models and connections
  - `extraction/` - OCR decision and PDF text extraction
  - `indexing/` - Text chunking and processing
  - `schemas/` - Pydantic models for validation
  - `services/` - File storage and utilities
  - `core/` - Configuration and settings
- `frontend/` - React + Vite frontend
- `models/` - Serialized ML models and metadata
- `storage/` - Local file storage for uploaded documents
- `docs/` - Project documentation
- `data/` - Training data and datasets

### Current API Surface

**System:**

- `GET /` - Welcome message
- `GET /health` - Health check endpoint

**Document Management:**

- `POST /documents/upload` - Upload a PDF document
- `GET /documents` - List all uploaded documents (newest first)
- `GET /documents/{document_id}` - Get document metadata

**OCR & Extraction:**

- `POST /documents/{document_id}/ocr-verdict` - Get OCR requirement prediction
- `POST /documents/{document_id}/extract` - Extract text from document
- `GET /documents/{document_id}/text` - Retrieve extracted text

**Chunking:**

- `POST /documents/{document_id}/chunk` - Chunk extracted text and persist

**Interactive Docs:**

- `GET /docs` - Swagger UI (interactive API explorer)
- `GET /redoc` - ReDoc (alternative API documentation)

### Reference Notes

- The project is intentionally being built in stages.
- The documentation should be updated as each new subsystem is added.
- Keep architecture notes close to implementation reality so the docs remain useful as engineering records.
- API endpoints follow explicit document processing stages to maintain clarity and testability.
- Each pipeline stage (upload → extract → chunk) is independently callable for flexibility.
