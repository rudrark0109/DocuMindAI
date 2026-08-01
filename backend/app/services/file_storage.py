from pathlib import Path
from fastapi import UploadFile
from backend.app.core.config import settings
from backend.app.services.document_id_service import generate_document_code

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_CHUNK_SIZE = 1024 * 1024


class FileTooLargeError(ValueError):
    pass

async def save_uploaded_file(file: UploadFile) -> dict:
       
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    original_filename = Path(file.filename or "document").name
    file_extension = Path(original_filename).suffix

    document_code = generate_document_code(original_filename)

    saved_filename = f"{document_code}{file_extension}"
    file_path = UPLOAD_DIR / saved_filename
    max_size = settings.max_upload_size_mb * 1024 * 1024
    file_size = 0

    try:
        with open(file_path, "wb") as destination:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                file_size += len(chunk)
                if file_size > max_size:
                    raise FileTooLargeError(
                        f"File exceeds the {settings.max_upload_size_mb} MB limit."
                    )
                destination.write(chunk)
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    return {
        "document_code": document_code,
        "original_filename": original_filename,
        "saved_filename": saved_filename,
        "file_size": file_size,
        "file_path": str(file_path),
        "content_type": file.content_type
    }


def delete_saved_file(file_path: str) -> None:
    """Remove a persisted upload when its database workflow cannot complete."""
    Path(file_path).unlink(missing_ok=True)
