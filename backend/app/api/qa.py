from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.rag.providers import RAGProviderError
from backend.app.rag.service import RAGDocumentNotFound, answer_question
from backend.app.schemas.schemas import ChatRequest, QARequest, QAResponse


router = APIRouter(tags=["Grounded Q&A"])


async def _answer(request: QARequest, db: Session, *, document_id: str | None = None):
    try:
        return await run_in_threadpool(
            answer_question,
            request.question,
            db,
            document_id=document_id,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )
    except RAGDocumentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RAGProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/documents/{document_id}/qa",
    response_model=QAResponse,
    summary="Answer from one document with grounded citations",
)
async def document_question(
    document_id: str,
    request: QARequest,
    db: Session = Depends(get_db),
):
    return await _answer(request, db, document_id=document_id)


@router.post(
    "/chat",
    response_model=QAResponse,
    summary="Answer across the document collection with grounded citations",
)
async def collection_question(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    try:
        return await run_in_threadpool(
            answer_question,
            request.question,
            db,
            document_ids=request.document_ids,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )
    except RAGDocumentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RAGProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
