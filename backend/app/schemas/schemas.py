from datetime import datetime
from pydantic import BaseModel

class DocumentResponse(BaseModel):
    id: str
    document_code: str
    original_filename: str
    saved_filename: str
    file_path: str
    content_type: str
    file_size: int
    processing_status: str
    created_at: datetime

    class Config:
        from_attributes = True
