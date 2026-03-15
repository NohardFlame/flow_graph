"""Add source_parts_jsonb to document_versions for multi-file support.

Revision ID: 002
Revises: 001
Create Date: Add source_parts for multi-part document versions

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_versions",
        sa.Column("source_parts_jsonb", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_versions", "source_parts_jsonb")
