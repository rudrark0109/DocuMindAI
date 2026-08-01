from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260801_05"
down_revision: Union[str, None] = "20260801_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("source_format", sa.String(), nullable=True))
    op.add_column("document_chunks", sa.Column("heading_path", sa.Text(), nullable=True))
    op.add_column("document_chunks", sa.Column("block_types", sa.Text(), nullable=True))
    op.add_column("document_chunks", sa.Column("previous_chunk_id", sa.String(), nullable=True))
    op.add_column("document_chunks", sa.Column("next_chunk_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_chunks", "next_chunk_id")
    op.drop_column("document_chunks", "previous_chunk_id")
    op.drop_column("document_chunks", "block_types")
    op.drop_column("document_chunks", "heading_path")
    op.drop_column("document_chunks", "source_format")
