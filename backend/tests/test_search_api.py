import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from backend.app.api.search import semantic_search
from backend.app.schemas.schemas import SearchRequest


class SearchRequestTests(unittest.TestCase):
    def test_trims_query_and_applies_defaults(self):
        request = SearchRequest(query="  invoice total  ")

        self.assertEqual(request.query, "invoice total")
        self.assertEqual(request.top_k, 5)
        self.assertEqual(request.similarity_threshold, 0.0)

    def test_rejects_blank_query(self):
        with self.assertRaises(ValidationError):
            SearchRequest(query="   ")

    def test_rejects_invalid_limits(self):
        with self.assertRaises(ValidationError):
            SearchRequest(query="invoice", top_k=0)
        with self.assertRaises(ValidationError):
            SearchRequest(query="invoice", top_k=51)
        with self.assertRaises(ValidationError):
            SearchRequest(query="invoice", similarity_threshold=1.1)


class SearchAPITests(unittest.TestCase):
    @patch(
        "backend.app.api.search.run_in_threadpool",
        new_callable=AsyncMock,
    )
    def test_returns_search_metadata_and_results(self, threadpool):
        threadpool.return_value = [
            {
                "document_id": "document-1",
                "document_code": "DOC-001",
                "original_filename": "invoice.pdf",
                "chunk_id": "chunk-1",
                "chunk_index": 0,
                "text": "Invoice total is $125.",
                "preview": "Invoice total is $125.",
                "similarity": 0.91,
            }
        ]
        request = SearchRequest(
            query="invoice total",
            top_k=3,
            similarity_threshold=0.5,
            document_id="document-1",
        )
        db = MagicMock()

        response = asyncio.run(semantic_search(request, db))

        self.assertEqual(response["result_count"], 1)
        self.assertEqual(response["results"][0]["similarity"], 0.91)
        args, kwargs = threadpool.call_args
        self.assertEqual(args[1], "invoice total")
        self.assertIs(args[2], db)
        self.assertEqual(kwargs["top_k"], 3)
        self.assertEqual(kwargs["similarity_threshold"], 0.5)
        self.assertEqual(kwargs["document_id"], "document-1")

    @patch(
        "backend.app.api.search.run_in_threadpool",
        new_callable=AsyncMock,
    )
    def test_returns_empty_result_set(self, threadpool):
        threadpool.return_value = []

        response = asyncio.run(
            semantic_search(SearchRequest(query="missing"), MagicMock())
        )

        self.assertEqual(response["result_count"], 0)
        self.assertEqual(response["results"], [])
