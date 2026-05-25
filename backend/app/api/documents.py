from fastapi import APIRouter, HTTPException, UploadFile, File
from backend.app.services.file_storage import save_uploaded_file

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg"
]

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Endpoint to upload a document. Accepts PDF and image files (JPEG, PNG, JPG).
    Args:
        file (UploadFile): The file to be uploaded."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF and image files (JPEG, PNG, JPG) are allowed.")

    saved_file_info = await save_uploaded_file(file)
    return {
        "message": "File uploaded successfully",
        "original_filename": saved_file_info["original_filename"],
        "saved_filename": saved_file_info["saved_filename"],
        "file_size": saved_file_info["file_size"],
        "file_path": saved_file_info["file_path"],
        "content_type": saved_file_info["content_type"]
    }
