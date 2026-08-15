"""Add slug column for SEO-friendly article URLs.

Revision ID: 003
Revises: 002
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "synthesized_stories",
        sa.Column("slug", sa.String(length=256), nullable=True),
    )
    op.create_index(
        op.f("ix_synthesized_stories_slug"),
        "synthesized_stories",
        ["slug"],
        unique=True,
    )

    # Backfill existing rows with title-based slug + id suffix
    op.execute(
        sa.text(
            """
            UPDATE synthesized_stories
            SET slug = (
                trim(both '-' from regexp_replace(
                    lower(regexp_replace(title, '[^\\w\\s-]', '', 'g')),
                    '[\\s_-]+', '-', 'g'
                ))
                || '-' || left(replace(id::text, '-', ''), 6)
            )
            WHERE slug IS NULL
            """
        )
    )

    op.alter_column("synthesized_stories", "slug", nullable=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_synthesized_stories_slug"), table_name="synthesized_stories")
    op.drop_column("synthesized_stories", "slug")
