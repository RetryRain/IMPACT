"""Add priority column for feed ordering.

Revision ID: 002
Revises: 001
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "synthesized_stories",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_synthesized_stories_priority_published_at",
        "synthesized_stories",
        ["priority", "published_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_synthesized_stories_priority_published_at",
        table_name="synthesized_stories",
    )
    op.drop_column("synthesized_stories", "priority")
