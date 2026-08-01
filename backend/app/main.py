from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.routes import api_router
from backend.app.core.config import settings

app = FastAPI(title="DocuMindAI", description="An AI-powered document management system", version="1.2.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
def root():
    return {"message": "Welcome to DocuMindAI!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
