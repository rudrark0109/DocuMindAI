import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.rag.providers import ExtractiveProvider, ProviderAnswer
from backend.app.rag.service import answer_question


def evidence():
    return [
        {
            "document_id": "document-1",
            "document_code": "DOC-001",
            "original_filename": "report.pdf",
            "chunk_id": "chunk-1",
            "chunk_index": 0,
            "text": "Quarterly revenue was 42 million dollars.",
            "preview": "Quarterly revenue was 42 million dollars.",
            "similarity": 0.88,
            "source_page_start": 2,
            "source_page_end": 2,
            "source_location": {"page_start": 2, "page_end": 2},
            "chunker_version": "fixed-window-v1",
        }
    ]


class RAGProviderTests(unittest.TestCase):
    def test_extractive_provider_returns_evidence_and_citation(self):
        result = ExtractiveProvider().generate("What was quarterly revenue?", evidence())

        self.assertFalse(result.abstain)
        self.assertEqual(result.citation_ids, ["C1"])
        self.assertIn("42 million", result.answer)

    def test_extractive_provider_abstains_without_term_overlap(self):
        result = ExtractiveProvider().generate("What is the hiring plan?", evidence())

        self.assertTrue(result.abstain)
        self.assertEqual(result.citation_ids, [])


class RAGServiceTests(unittest.TestCase):
    @patch("backend.app.rag.service.configured_provider")
    @patch("backend.app.rag.service.search_document_chunks")
    def test_single_document_scope_is_forwarded_and_citations_are_structured(
        self,
        search,
        provider_factory,
    ):
        search.return_value = evidence()
        provider_factory.return_value = ExtractiveProvider()
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [("document-1",)]

        result = answer_question(
            "What was quarterly revenue?",
            db,
            document_id="document-1",
        )

        self.assertEqual(result["scope"], "document")
        self.assertEqual(result["citations"][0]["citation_id"], "C1")
        self.assertEqual(result["citations"][0]["source_page_start"], 2)
        self.assertEqual(search.call_args.kwargs["document_id"], "document-1")
        self.assertIsNone(search.call_args.kwargs["document_ids"])

    @patch("backend.app.rag.service.configured_provider")
    @patch("backend.app.rag.service.search_document_chunks")
    def test_invalid_provider_citations_are_rejected(self, search, provider_factory):
        search.return_value = evidence()
        provider_factory.return_value = SimpleNamespace(
            generate=lambda question, items: ProviderAnswer(
                answer="unsupported claim",
                citation_ids=["C999"],
                abstain=False,
                provider="test",
                model="test",
            )
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        result = answer_question("What was quarterly revenue?", db)

        self.assertTrue(result["insufficient_evidence"])
        self.assertEqual(result["citations"], [])
        self.assertIn("not contain enough", result["answer"])


if __name__ == "__main__":
    unittest.main()
