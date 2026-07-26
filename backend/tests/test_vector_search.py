import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.retrieval.vector_search import search_document_chunks


class VectorSearchTests(unittest.TestCase):
    @patch("backend.app.retrieval.vector_search.generate_embedding")
    def test_maps_ranked_database_rows(self, generate_embedding):
        generate_embedding.return_value = [0.1] * 384
        chunk = SimpleNamespace(
            id="chunk-1",
            document_id="document-1",
            chunk_index=2,
            chunk_text="A" * 300,
        )
        document = SimpleNamespace(
            id="document-1",
            document_code="DOC-001",
            original_filename="manual.pdf",
        )
        db = MagicMock()
        (
            db.query.return_value.join.return_value.filter.return_value
            .filter.return_value.order_by.return_value.limit.return_value.all
        ).return_value = [(chunk, document, 0.12)]

        results = search_document_chunks(
            "installation steps",
            db,
            top_k=3,
            similarity_threshold=0.5,
        )

        self.assertEqual(results[0]["similarity"], 0.88)
        self.assertEqual(len(results[0]["preview"]), 240)
        self.assertEqual(results[0]["chunk_index"], 2)
        generate_embedding.assert_called_once_with("installation steps")

    @patch("backend.app.retrieval.vector_search.generate_embedding")
    def test_returns_empty_list_when_nothing_matches(self, generate_embedding):
        generate_embedding.return_value = [0.1] * 384
        db = MagicMock()
        (
            db.query.return_value.join.return_value.filter.return_value
            .filter.return_value.order_by.return_value.limit.return_value.all
        ).return_value = []

        self.assertEqual(search_document_chunks("missing", db), [])
