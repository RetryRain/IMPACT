"""Add GIN index on source_urls for fast URL lookups.

Revision ID: 005
Revises: 004
Create Date: 2026-08-17
"""

from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_synthesized_stories_source_urls_gin "
        "ON synthesized_stories USING gin (source_urls)"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_synthesized_stories_source_urls_gin",
        table_name="synthesized_stories",
    )
