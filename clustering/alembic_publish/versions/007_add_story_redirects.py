"""Add story_redirects for purged article URLs.

Revision ID: 007
Revises: 006
Create Date: 2026-08-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "story_redirects",
        sa.Column("story_id", UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("slug", sa.String(length=256), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("story_id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        op.f("ix_story_redirects_slug"),
        "story_redirects",
        ["slug"],
        unique=True,
    )
    op.create_index(
        op.f("ix_story_redirects_scope"),
        "story_redirects",
        ["scope"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_story_redirects_scope"), table_name="story_redirects")
    op.drop_index(op.f("ix_story_redirects_slug"), table_name="story_redirects")
    op.drop_table("story_redirects")
