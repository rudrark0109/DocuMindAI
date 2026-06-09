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

## Current Implementation

### Implemented Backend Features

- FastAPI backend is operational
- `POST /documents/upload`
- `GET /documents`
- `GET /documents/{document_id}`

### Upload Pipeline

The current upload pipeline performs the following steps:

1. Validate the file type
2. Generate a custom document code
3. Store the file locally
4. Store metadata in PostgreSQL

### Database Metadata

The database stores metadata only, including:

- internal UUID
- document code
- original filename
- saved filename
- file path
- content type
- processing status
- created time

The document file itself stays on the filesystem.

## OCR Decision Engine

### Purpose

The OCR Decision Engine determines whether OCR is needed before OCR is performed.

This is a key differentiator in the project because many systems either OCR everything or skip OCR entirely. DocuMind AI routes documents based on evidence.

### Why It Matters

- OCR is expensive.
- Many PDFs already contain usable digital text.
- Running OCR unnecessarily wastes time and compute.
- Selective OCR improves throughput and makes the pipeline more intelligent.

### Dataset Notes

The current labeled dataset includes:

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

The current model produced perfect scores on the small evaluation set and also surfaced at least one human labeling mistake. That is useful, but it should be treated as a promising signal rather than a final-world claim.

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

### Downstream Goals

- chunking
- embedding generation
- vector storage
- semantic search
- RAG with citations

## Development Log

This file records meaningful implementation milestones and decisions.

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

- `backend/`
- `frontend/`
- `models/`
- `notebooks/`
- `storage/`
- `data/`

### Current API Surface

- `GET /`
- `GET /health`
- `POST /documents/upload`
- `GET /documents`
- `GET /documents/{document_id}`

### Reference Notes

- The project is intentionally being built in stages.
- The documentation should be updated as each new subsystem is added.
- Keep architecture notes close to implementation reality so the docs remain useful as engineering records.
