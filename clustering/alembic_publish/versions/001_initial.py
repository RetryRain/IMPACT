"""Initial publish schema for synthesized stories.

Revision ID: 001
Revises:
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "synthesized_stories",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("author", sa.String(length=256), nullable=True),
        sa.Column("image", sa.String(length=2048), nullable=True),
        sa.Column("tags", JSONB(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("scope", sa.String(length=64), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_urls", JSONB(), nullable=False),
        sa.Column("sources", JSONB(), nullable=False),
        sa.Column("synthesized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cluster_id"),
    )
    op.create_index(
        op.f("ix_synthesized_stories_cluster_id"),
        "synthesized_stories",
        ["cluster_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_synthesized_stories_scope"),
        "synthesized_stories",
        ["scope"],
        unique=False,
    )
    op.create_index(
        op.f("ix_synthesized_stories_published_at"),
        "synthesized_stories",
        ["published_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_synthesized_stories_synthesized_at"),
        "synthesized_stories",
        ["synthesized_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_synthesized_stories_synthesized_at"),
        table_name="synthesized_stories",
    )
    op.drop_index(
        op.f("ix_synthesized_stories_published_at"),
        table_name="synthesized_stories",
    )
    op.drop_index(
        op.f("ix_synthesized_stories_scope"),
        table_name="synthesized_stories",
    )
    op.drop_index(
        op.f("ix_synthesized_stories_cluster_id"),
        table_name="synthesized_stories",
    )
    op.drop_table("synthesized_stories")
