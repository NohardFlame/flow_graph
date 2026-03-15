"""Add constituent_chunk_hashes to chunks for glued batch extraction.

Revision ID: 003
Revises: 002
Create Date: Add constituent_chunk_hashes for composite batch chunks

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column("constituent_chunk_hashes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chunks", "constituent_chunk_hashes")
