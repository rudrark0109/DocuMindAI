import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app.indexing.indexing_pipeline import rebuild_document_index


class IndexingPipelineTests(unittest.TestCase):
    @patch("backend.app.indexing.indexing_pipeline.generate_embeddings")
    @patch("backend.app.indexing.indexing_pipeline.chunk_text")
    def test_atomically_replaces_chunks_and_embeddings(self, chunk, embed):
        chunk.return_value = [
            {
                "chunk_index": 0,
                "text": "indexed content",
                "word_count": 2,
                "char_count": 15,
                "start_word_index": 0,
                "end_word_index": 1,
            }
        ]
        embed.return_value = [[0.1] * 384]
        document = SimpleNamespace(
            id="document-1",
            extracted_text="indexed content",
            processing_status="text_extracted",
        )
        db = MagicMock()

        result = rebuild_document_index(document, db)

        db.query.return_value.filter.return_value.delete.assert_called_once_with(
            synchronize_session=False
        )
        added_chunk = db.add.call_args.args[0]
        self.assertEqual(added_chunk.chunk_index, 0)
        self.assertEqual(len(added_chunk.embedding), 384)
        self.assertEqual(added_chunk.embedding_status, "embedded")
        self.assertEqual(document.processing_status, "embedded")
        self.assertEqual(result["embedded_chunk_count"], 1)
        db.commit.assert_called_once()
        db.rollback.assert_not_called()

    def test_rejects_document_without_extracted_text(self):
        document = SimpleNamespace(id="document-1", extracted_text="")

        with self.assertRaisesRegex(ValueError, "no extracted text"):
            rebuild_document_index(document, MagicMock())

    @patch("backend.app.indexing.indexing_pipeline.generate_embeddings")
    @patch("backend.app.indexing.indexing_pipeline.chunk_text")
    def test_rolls_back_database_failure(self, chunk, embed):
        chunk.return_value = [
            {
                "chunk_index": 0,
                "text": "indexed content",
                "word_count": 2,
                "char_count": 15,
                "start_word_index": 0,
                "end_word_index": 1,
            }
        ]
        embed.return_value = [[0.1] * 384]
        document = SimpleNamespace(
            id="document-1",
            extracted_text="indexed content",
            processing_status="text_extracted",
        )
        db = MagicMock()
        db.commit.side_effect = RuntimeError("database unavailable")

        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            rebuild_document_index(document, db)

        db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
