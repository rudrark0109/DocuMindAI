from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_03"
down_revision: Union[str, None] = "20260727_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("extracted_pages", sa.Text(), nullable=True))
    op.add_column(
        "document_chunks",
        sa.Column("source_page_start", sa.Integer(), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("source_page_end", sa.Integer(), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("source_location", sa.Text(), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column(
            "chunker_version",
            sa.String(),
            nullable=False,
            server_default="fixed-window-v1",
        ),
    )
    op.alter_column("document_chunks", "chunker_version", server_default=None)


def downgrade() -> None:
    op.drop_column("document_chunks", "chunker_version")
    op.drop_column("document_chunks", "source_location")
    op.drop_column("document_chunks", "source_page_end")
    op.drop_column("document_chunks", "source_page_start")
    op.drop_column("documents", "extracted_pages")
