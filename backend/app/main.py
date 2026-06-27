from fastapi import FastAPI
from backend.app.api.routes import api_router
from backend.app.db.database import engine, Base
from backend.app.db import models
from backend.app.db import chunk_model

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DocuMindAI", description="An AI-powered document management system", version="1.0.0")

app.include_router(api_router)

@app.get("/")
def root():
    return {"message": "Welcome to DocuMindAI!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}