"""Create the document indexing schema.

Revision ID: 20260724_01
Revises:
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


revision: str = "20260724_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if not inspector.has_table("documents"):
        op.create_table(
            "documents",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("document_code", sa.String(), nullable=False),
            sa.Column("original_filename", sa.String(), nullable=False),
            sa.Column("saved_filename", sa.String(), nullable=False),
            sa.Column("file_path", sa.String(), nullable=False),
            sa.Column("content_type", sa.String(), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("processing_status", sa.String(), nullable=False),
            sa.Column("ocr_required", sa.String(), nullable=True),
            sa.Column("ocr_confidence", sa.String(), nullable=True),
            sa.Column("ocr_model_version", sa.String(), nullable=True),
            sa.Column("extracted_text", sa.Text(), nullable=True),
            sa.Column("extraction_method", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("document_code"),
        )
        op.create_index("ix_documents_id", "documents", ["id"])
        op.create_index("ix_documents_document_code", "documents", ["document_code"])

    inspector = sa.inspect(bind)
    if not inspector.has_table("document_chunks"):
        op.create_table(
            "document_chunks",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("document_id", sa.String(), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("chunk_text", sa.Text(), nullable=False),
            sa.Column("word_count", sa.Integer(), nullable=False),
            sa.Column("character_count", sa.Integer(), nullable=False),
            sa.Column("start_word_index", sa.Integer(), nullable=True),
            sa.Column("end_word_index", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("embedding", Vector(384), nullable=True),
            sa.Column("embedding_model", sa.String(), nullable=True),
            sa.Column("embedding_status", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "document_id",
                "chunk_index",
                name="uq_document_chunks_document_index",
            ),
        )
        op.create_index("ix_document_chunks_id", "document_chunks", ["id"])
        op.create_index(
            "ix_document_chunks_document_id",
            "document_chunks",
            ["document_id"],
        )
    else:
        constraints = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("document_chunks")
        }
        if "uq_document_chunks_document_index" not in constraints:
            op.create_unique_constraint(
                "uq_document_chunks_document_index",
                "document_chunks",
                ["document_id", "chunk_index"],
            )


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_table("documents")
