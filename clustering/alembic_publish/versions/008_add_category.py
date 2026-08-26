"""Add category column for news classification.

Revision ID: 008
Revises: 007
Create Date: 2026-08-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "synthesized_stories",
        sa.Column("category", sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f("ix_synthesized_stories_category"),
        "synthesized_stories",
        ["category"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_synthesized_stories_category"),
        table_name="synthesized_stories",
    )
    op.drop_column("synthesized_stories", "category")
