from fastapi import APIRouter
from backend.app.api.documents import router as documents_router
from backend.app.api.search import router as search_router

api_router = APIRouter()
api_router.include_router(documents_router)
api_router.include_router(search_router)
