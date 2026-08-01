from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260801_04"
down_revision: Union[str, None] = "20260728_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("source_format", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("normalized_blocks", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("extraction_warnings", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "extraction_warnings")
    op.drop_column("documents", "normalized_blocks")
    op.drop_column("documents", "source_format")
