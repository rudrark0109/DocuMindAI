from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.indexing.embedding_generator import EMBEDDING_MODEL_NAME
from backend.app.retrieval.vector_search import search_document_chunks
from backend.app.schemas.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: Session = Depends(get_db),
):
    results = await run_in_threadpool(
        search_document_chunks,
        request.query,
        db,
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold,
        document_id=request.document_id,
    )
    return {
        "query": request.query,
        "result_count": len(results),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "results": results,
    }
