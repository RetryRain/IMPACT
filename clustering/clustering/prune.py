from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, exists, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from clustering.config import get_settings
from clustering.db.dropped_models import DroppedArticle
from clustering.db.dropped_session import get_dropped_session
from clustering.db.models import Article, ArticleEmbedding, StoryCluster
from clustering.db.publish_models import StoryRedirect, SynthesizedStory
from clustering.db.publish_session import get_publish_session
from clustering.db.session import get_session
from clustering.log import info
from clustering.timezone_util import IST

BYTES_PER_MB = 1024 * 1024


def _cutoff(retention_days: int) -> datetime:
    return datetime.now(IST) - timedelta(days=retention_days)


def _database_size_bytes(session: Session) -> int:
    size = session.scalar(text("SELECT pg_database_size(current_database())"))
    return int(size or 0)


def _should_prune(session: Session) -> tuple[bool, int]:
    settings = get_settings()
    limit_bytes = settings.db_size_limit_mb * BYTES_PER_MB
    size_bytes = _database_size_bytes(session)
    return size_bytes >= limit_bytes, size_bytes


def _story_age_cutoff(cutoff: datetime):
    return func.coalesce(
        SynthesizedStory.published_at,
        SynthesizedStory.created_at,
    ) < cutoff


def _article_age_cutoff(cutoff: datetime):
    return func.coalesce(Article.published_at, Article.created_at) < cutoff


def prune_publish_database() -> dict[str, Any]:
    settings = get_settings()
    cutoff = _cutoff(settings.retention_days)
    stats: dict[str, Any] = {
        "database": "publish",
        "pruned": False,
        "redirects_written": 0,
        "stories_deleted": 0,
    }

    with get_publish_session() as session:
        should_prune, size_bytes = _should_prune(session)
        stats["size_mb"] = round(size_bytes / BYTES_PER_MB, 2)
        if not should_prune:
            return stats

        stats["pruned"] = True
        old_stories = list(
            session.scalars(
                select(SynthesizedStory).where(_story_age_cutoff(cutoff))
            ).all()
        )
        if not old_stories:
            return stats

        old_ids = [story.id for story in old_stories]
        for story in old_stories:
            if not story.slug or not story.scope or not story.url:
                continue
            stmt = (
                insert(StoryRedirect)
                .values(
                    story_id=story.id,
                    scope=story.scope,
                    slug=story.slug,
                    source_url=story.url,
                )
                .on_conflict_do_update(
                    index_elements=[StoryRedirect.story_id],
                    set_={
                        "scope": story.scope,
                        "slug": story.slug,
                        "source_url": story.url,
                    },
                )
            )
            session.execute(stmt)
            stats["redirects_written"] += 1

        session.execute(
            update(SynthesizedStory)
            .where(SynthesizedStory.canonical_story_id.in_(old_ids))
            .values(canonical_story_id=None)
        )
        session.execute(
            delete(SynthesizedStory).where(SynthesizedStory.id.in_(old_ids))
        )
        stats["stories_deleted"] = len(old_ids)

    return stats


def prune_clustering_database() -> dict[str, Any]:
    settings = get_settings()
    cutoff = _cutoff(settings.retention_days)
    stats: dict[str, Any] = {
        "database": "clustering",
        "pruned": False,
        "articles_deleted": 0,
        "clusters_deleted": 0,
    }

    with get_session() as session:
        should_prune, size_bytes = _should_prune(session)
        stats["size_mb"] = round(size_bytes / BYTES_PER_MB, 2)
        if not should_prune:
            return stats

        stats["pruned"] = True
        old_article_ids = list(
            session.scalars(
                select(Article.id).where(_article_age_cutoff(cutoff))
            ).all()
        )
        if not old_article_ids:
            return stats

        session.execute(
            delete(ArticleEmbedding).where(
                ArticleEmbedding.article_id.in_(old_article_ids)
            )
        )
        session.execute(
            update(StoryCluster)
            .where(StoryCluster.representative_article_id.in_(old_article_ids))
            .values(representative_article_id=None)
        )
        session.execute(delete(Article).where(Article.id.in_(old_article_ids)))
        stats["articles_deleted"] = len(old_article_ids)

        orphan_clusters = list(
            session.scalars(
                select(StoryCluster.id).where(
                    ~exists().where(Article.cluster_id == StoryCluster.id)
                )
            ).all()
        )
        if orphan_clusters:
            session.execute(
                delete(StoryCluster).where(StoryCluster.id.in_(orphan_clusters))
            )
            stats["clusters_deleted"] = len(orphan_clusters)

    return stats


def prune_dropped_database() -> dict[str, Any]:
    settings = get_settings()
    cutoff = _cutoff(settings.retention_days)
    stats: dict[str, Any] = {
        "database": "dropped",
        "pruned": False,
        "rows_deleted": 0,
    }

    with get_dropped_session() as session:
        should_prune, size_bytes = _should_prune(session)
        stats["size_mb"] = round(size_bytes / BYTES_PER_MB, 2)
        if not should_prune:
            return stats

        stats["pruned"] = True
        result = session.execute(
            delete(DroppedArticle).where(DroppedArticle.dropped_at < cutoff)
        )
        stats["rows_deleted"] = result.rowcount or 0

    return stats


def prune_feedback_database() -> dict[str, Any]:
    settings = get_settings()
    stats: dict[str, Any] = {
        "database": "feedback",
        "pruned": False,
        "rows_deleted": 0,
        "skipped": False,
    }

    if not settings.feedback_database_url:
        stats["skipped"] = True
        return stats

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    cutoff = _cutoff(settings.retention_days)
    engine = create_engine(settings.feedback_database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        should_prune, size_bytes = _should_prune(session)
        stats["size_mb"] = round(size_bytes / BYTES_PER_MB, 2)
        if not should_prune:
            return stats

        stats["pruned"] = True
        result = session.execute(
            text("DELETE FROM feedback WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        session.commit()
        stats["rows_deleted"] = result.rowcount or 0

    return stats


def prune_all_databases() -> dict[str, Any]:
    info("Checking database sizes for retention prune...")
    results = {
        "publish": prune_publish_database(),
        "clustering": prune_clustering_database(),
        "dropped": prune_dropped_database(),
        "feedback": prune_feedback_database(),
    }
    limit_mb = get_settings().db_size_limit_mb
    for name, result in results.items():
        if result.get("pruned"):
            info(f"  pruned {name}: {result}")
        elif result.get("skipped"):
            info(f"  skipped {name} (not configured)")
        else:
            info(f"  {name}: {result.get('size_mb', '?')} MB (under {limit_mb} MB limit)")
    return results
