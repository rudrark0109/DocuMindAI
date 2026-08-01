from fastapi import APIRouter
from backend.app.api.documents import router as documents_router
from backend.app.api.search import router as search_router
from backend.app.api.qa import router as qa_router

api_router = APIRouter()
api_router.include_router(documents_router)
api_router.include_router(search_router)
api_router.include_router(qa_router)
