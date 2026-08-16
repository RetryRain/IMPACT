"""Add canonical_story_id column.

Revision ID: 004
Revises: 003
Create Date: 2026-08-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "synthesized_stories",
        sa.Column("canonical_story_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_synthesized_stories_canonical_story_id",
        "synthesized_stories",
        "synthesized_stories",
        ["canonical_story_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_synthesized_stories_canonical_story_id"),
        "synthesized_stories",
        ["canonical_story_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_synthesized_stories_canonical_story_id"),
        table_name="synthesized_stories",
    )
    op.drop_constraint(
        "fk_synthesized_stories_canonical_story_id",
        "synthesized_stories",
        type_="foreignkey",
    )
    op.drop_column("synthesized_stories", "canonical_story_id")
