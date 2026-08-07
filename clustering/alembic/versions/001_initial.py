"""Initial schema for articles, embeddings, and story clusters.

Revision ID: 001
Revises:
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    cluster_status = sa.Enum(
        "open", "ready_for_llm", "synthesized", name="cluster_status"
    )

    op.create_table(
        "story_clusters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("representative_article_id", sa.UUID(), nullable=True),
        sa.Column("title_hint", sa.String(length=512), nullable=True),
        sa.Column("scope", sa.String(length=64), nullable=True),
        sa.Column("first_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("article_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            cluster_status,
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_story_clusters_scope_last_published",
        "story_clusters",
        ["scope", "last_published_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_story_clusters_scope"), "story_clusters", ["scope"], unique=False
    )
    op.create_index(
        op.f("ix_story_clusters_last_published_at"),
        "story_clusters",
        ["last_published_at"],
        unique=False,
    )

    op.create_table(
        "articles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("scope", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("author", sa.String(length=256), nullable=True),
        sa.Column("image", sa.String(length=2048), nullable=True),
        sa.Column("tags", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cluster_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cluster_id"], ["story_clusters.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(op.f("ix_articles_url"), "articles", ["url"], unique=True)
    op.create_index(op.f("ix_articles_scope"), "articles", ["scope"], unique=False)
    op.create_index(
        op.f("ix_articles_published_at"), "articles", ["published_at"], unique=False
    )
    op.create_index(
        op.f("ix_articles_cluster_id"), "articles", ["cluster_id"], unique=False
    )

    op.create_foreign_key(
        "fk_story_clusters_representative_article",
        "story_clusters",
        "articles",
        ["representative_article_id"],
        ["id"],
    )

    op.create_table(
        "article_embeddings",
        sa.Column("article_id", sa.UUID(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.PrimaryKeyConstraint("article_id"),
    )

    op.execute(
        """
        CREATE INDEX ix_article_embeddings_embedding_hnsw
        ON article_embeddings
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_article_embeddings_embedding_hnsw", table_name="article_embeddings")
    op.drop_table("article_embeddings")
    op.drop_constraint(
        "fk_story_clusters_representative_article", "story_clusters", type_="foreignkey"
    )
    op.drop_table("articles")
    op.drop_index("ix_story_clusters_scope_last_published", table_name="story_clusters")
    op.drop_table("story_clusters")
    op.execute("DROP TYPE IF EXISTS cluster_status")
