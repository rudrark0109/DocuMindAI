import asyncio
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from backend.app.services.file_storage import FileTooLargeError, save_uploaded_file


class AsyncUpload:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.content_type = "application/pdf"
        self._file = BytesIO(content)

    async def read(self, size: int) -> bytes:
        return self._file.read(size)


class FileStorageTests(unittest.TestCase):
    def test_streams_upload_to_disk(self):
        with tempfile.TemporaryDirectory() as upload_dir:
            upload = AsyncUpload("document.pdf", b"pdf-content")
            with (
                patch(
                    "backend.app.services.file_storage.UPLOAD_DIR",
                    Path(upload_dir),
                ),
                patch(
                    "backend.app.services.file_storage.generate_document_code",
                    return_value="DOC-001",
                ),
            ):
                result = asyncio.run(save_uploaded_file(upload))

            self.assertEqual(result["file_size"], 11)
            self.assertEqual(Path(result["file_path"]).read_bytes(), b"pdf-content")

    def test_removes_partial_file_when_size_limit_is_exceeded(self):
        with tempfile.TemporaryDirectory() as upload_dir:
            upload = AsyncUpload("large.pdf", b"too-large")
            with (
                patch(
                    "backend.app.services.file_storage.UPLOAD_DIR",
                    Path(upload_dir),
                ),
                patch(
                    "backend.app.services.file_storage.settings.max_upload_size_mb",
                    0,
                ),
                patch(
                    "backend.app.services.file_storage.generate_document_code",
                    return_value="DOC-002",
                ),
            ):
                with self.assertRaises(FileTooLargeError):
                    asyncio.run(save_uploaded_file(upload))

            self.assertEqual(list(Path(upload_dir).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
