from datetime import datetime
from uuid import uuid4
from pathlib import Path

def generate_document_code(filename: str) -> str:
    file_extension = Path(filename).suffix.replace('.', '').upper()

    if file_extension == "JPEG":
        file_type = "JPEG"
    elif file_extension == "JPG":
        file_type = "JPG"
    elif file_extension == "PNG":
        file_type = "PNG"
    elif file_extension == "PDF":
        file_type = "PDF"
    else:
        file_type = "FILE"

    random_part = uuid4().hex[:6].upper()
    timestamp_part = datetime.utcnow().strftime('%Y%m%d%H%M%S')

    return f"{file_type}-{timestamp_part}-{random_part}"