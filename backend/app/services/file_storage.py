from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
from backend.app.services.document_id_service import generate_document_code

UPLOAD_DIR = Path("storage/uploads")

async def save_uploaded_file(file: UploadFile) -> dict:
       
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    original_filename = file.filename
    file_extension = Path(original_filename).suffix

    document_code = generate_document_code(original_filename)

    saved_filename = f"{document_code}{file_extension}"
    file_path = UPLOAD_DIR / saved_filename
    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)

    return {
        "document_code": document_code,
        "original_filename": original_filename,
        "saved_filename": saved_filename,
        "file_size": len(file_content),
        "file_path": str(file_path),
        "content_type": file.content_type
    }
