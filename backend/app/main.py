from fastapi import FastAPI
from backend.app.api.documents import router as documents_router

app = FastAPI(title="DocuMindAI", description="An AI-powered document management system", version="1.0.0")

app.include_router(documents_router)

@app.get("/")
def root():
    return {"message": "Welcome to DocuMindAI!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}