"""Add durable asynchronous processing metadata.

Revision ID: 20260727_02
Revises: 20260724_01
Create Date: 2026-07-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260727_02"
down_revision: Union[str, None] = "20260724_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("processing_stage", sa.String(), nullable=False, server_default="queued"),
    )
    op.add_column(
        "documents",
        sa.Column("processing_progress", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("documents", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("documents", sa.Column("worker_task_id", sa.String(), nullable=True))
    op.add_column(
        "documents", sa.Column("processing_started_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "documents", sa.Column("processing_completed_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "documents", sa.Column("updated_at", sa.DateTime(), nullable=True)
    )
    op.execute("UPDATE documents SET updated_at = created_at")
    op.alter_column("documents", "processing_stage", server_default=None)
    op.alter_column("documents", "processing_progress", server_default=None)
    op.alter_column("documents", "retry_count", server_default=None)


def downgrade() -> None:
    for column_name in (
        "updated_at",
        "processing_completed_at",
        "processing_started_at",
        "worker_task_id",
        "retry_count",
        "processing_error",
        "processing_progress",
        "processing_stage",
    ):
        op.drop_column("documents", column_name)
