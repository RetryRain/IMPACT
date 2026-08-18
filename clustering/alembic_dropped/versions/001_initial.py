"""Initial dropped-articles schema.

Revision ID: 001
Revises:
Create Date: 2026-08-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dropped_articles",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("drop_reason", sa.Text(), nullable=True),
        sa.Column("cluster_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "dropped_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(
        op.f("ix_dropped_articles_url"),
        "dropped_articles",
        ["url"],
        unique=True,
    )
    op.create_index(
        op.f("ix_dropped_articles_cluster_id"),
        "dropped_articles",
        ["cluster_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_dropped_articles_dropped_at"),
        "dropped_articles",
        ["dropped_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_dropped_articles_dropped_at"),
        table_name="dropped_articles",
    )
    op.drop_index(
        op.f("ix_dropped_articles_cluster_id"),
        table_name="dropped_articles",
    )
    op.drop_index(
        op.f("ix_dropped_articles_url"),
        table_name="dropped_articles",
    )
    op.drop_table("dropped_articles")
