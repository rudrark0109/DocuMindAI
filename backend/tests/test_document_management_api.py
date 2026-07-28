import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.api.documents import delete_document, rename_document
from backend.app.schemas.schemas import DocumentRenameRequest


class DocumentRenameRequestTests(unittest.TestCase):
    def test_accepts_and_trims_pdf_filename(self):
        request = DocumentRenameRequest(filename="  quarterly report.pdf  ")

        self.assertEqual(request.filename, "quarterly report.pdf")

    def test_rejects_paths_and_non_pdf_extensions(self):
        for filename in ("../report.pdf", "folder/report.pdf", "report.txt"):
            with self.subTest(filename=filename), self.assertRaises(ValidationError):
                DocumentRenameRequest(filename=filename)


class DocumentManagementApiTests(unittest.TestCase):
    def test_rename_updates_only_user_visible_filename(self):
        document = SimpleNamespace(
            id="document-1",
            original_filename="old.pdf",
            saved_filename="DOC-001.pdf",
            file_path="storage/uploads/DOC-001.pdf",
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = document

        result = rename_document(
            "document-1",
            DocumentRenameRequest(filename="renamed.pdf"),
            db,
        )

        self.assertIs(result, document)
        self.assertEqual(document.original_filename, "renamed.pdf")
        self.assertEqual(document.saved_filename, "DOC-001.pdf")
        self.assertEqual(document.file_path, "storage/uploads/DOC-001.pdf")
        db.commit.assert_called_once_with()
        db.refresh.assert_called_once_with(document)

    @patch("backend.app.api.documents.delete_saved_file")
    def test_delete_removes_chunks_record_and_stored_file(self, delete_file):
        document = SimpleNamespace(
            id="document-1",
            file_path="storage/uploads/DOC-001.pdf",
        )
        document_query = MagicMock()
        document_query.filter.return_value.first.return_value = document
        chunk_query = MagicMock()
        chunk_query.filter.return_value.delete.return_value = 2
        db = MagicMock()
        db.query.side_effect = [document_query, chunk_query]

        response = delete_document("document-1", db)

        chunk_query.filter.return_value.delete.assert_called_once_with(
            synchronize_session=False
        )
        db.delete.assert_called_once_with(document)
        db.commit.assert_called_once_with()
        delete_file.assert_called_once_with("storage/uploads/DOC-001.pdf")
        self.assertEqual(response.status_code, 204)

    def test_missing_document_returns_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as context:
            delete_document("missing", db)

        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
