from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile

UPLOAD_DIR = Path("storage/uploads")

async def save_uploaded_file(file: UploadFile) -> dict:
    """Saves an uploaded file to the server's storage directory.
    Args:
        file (UploadFile): The file to be saved.
    Returns:
        dict: A dictionary containing information about the saved file."""
    
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    original_filename = file.filename
    file_extension = Path(original_filename).suffix
    saved_filename = f"{uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / saved_filename
    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)

    return {
        "original_filename": original_filename,
        "saved_filename": saved_filename,
        "file_size": len(file_content),
        "file_path": str(file_path),
        "content_type": file.content_type
    }
