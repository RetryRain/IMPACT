from __future__ import annotations

from datetime import datetime, timedelta, timezone

from clustering.timezone_util import IST, to_ist_iso

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from clustering.config import get_settings
from clustering.db.models import Article, ArticleEmbedding, ClusterStatus, StoryCluster
from clustering.log import info


def _effective_threshold(article: Article, neighbor: Article, similarity: float) -> float:
    settings = get_settings()
    if (
        article.source
        and neighbor.source
        and article.source == neighbor.source
    ):
        return settings.same_source_threshold
    return settings.similarity_threshold


def _find_nearest_neighbor(
    session: Session,
    article: Article,
    embedding: list[float],
) -> tuple[Article | None, float]:
    settings = get_settings()
    if article.published_at is None:
        return None, -1.0

    window_start = article.published_at - timedelta(
        hours=settings.cluster_time_window_hours
    )
    window_end = article.published_at + timedelta(
        hours=settings.cluster_time_window_hours
    )

    distance_expr = ArticleEmbedding.embedding.cosine_distance(embedding)
    similarity_expr = (1 - distance_expr).label("similarity")

    stmt = (
        select(Article, similarity_expr)
        .join(ArticleEmbedding, ArticleEmbedding.article_id == Article.id)
        .where(Article.id != article.id)
        .where(Article.scope == article.scope)
        .where(Article.published_at.is_not(None))
        .where(Article.published_at >= window_start)
        .where(Article.published_at <= window_end)
        .order_by(distance_expr.asc())
        .limit(1)
    )

    row = session.execute(stmt).first()
    if row is None:
        return None, -1.0

    neighbor, similarity = row
    return neighbor, float(similarity)


def _create_cluster(session: Session, article: Article) -> StoryCluster:
    cluster = StoryCluster(
        representative_article_id=article.id,
        title_hint=article.title,
        scope=article.scope,
        first_published_at=article.published_at,
        last_published_at=article.published_at,
        article_count=1,
        status=ClusterStatus.OPEN,
    )
    session.add(cluster)
    session.flush()
    article.cluster_id = cluster.id
    return cluster


def _assign_to_cluster(
    session: Session, article: Article, cluster: StoryCluster
) -> None:
    article.cluster_id = cluster.id
    cluster.article_count += 1
    if article.published_at:
        if (
            cluster.first_published_at is None
            or article.published_at < cluster.first_published_at
        ):
            cluster.first_published_at = article.published_at
        if (
            cluster.last_published_at is None
            or article.published_at > cluster.last_published_at
        ):
            cluster.last_published_at = article.published_at
    cluster.status = ClusterStatus.OPEN


def assign_articles(session: Session, *, limit: int | None = None) -> dict[str, int]:
    query = (
        select(Article)
        .options(joinedload(Article.embedding))
        .where(Article.cluster_id.is_(None))
        .order_by(Article.published_at.asc().nulls_last(), Article.created_at.asc())
    )
    if limit is not None:
        query = query.limit(limit)

    articles = list(session.scalars(query).unique())
    assigned_existing = 0
    created_clusters = 0
    skipped = 0
    total = len(articles)

    if total:
        info(f"Assigning {total} unclustered articles ...")

    for index, article in enumerate(articles, start=1):
        if article.embedding is None:
            skipped += 1
            continue

        neighbor, similarity = _find_nearest_neighbor(
            session, article, article.embedding.embedding
        )

        if neighbor is not None:
            threshold = _effective_threshold(article, neighbor, similarity)
            if similarity >= threshold and neighbor.cluster_id is not None:
                cluster = session.get(StoryCluster, neighbor.cluster_id)
                if cluster is not None:
                    _assign_to_cluster(session, article, cluster)
                    assigned_existing += 1
                    if index % 50 == 0 or index == total:
                        info(
                            f"  assigned {index}/{total} "
                            f"(joined={assigned_existing}, "
                            f"new_clusters={created_clusters}, skipped={skipped})"
                        )
                    continue

        _create_cluster(session, article)
        created_clusters += 1

        if index % 50 == 0 or index == total:
            info(
                f"  assigned {index}/{total} "
                f"(joined={assigned_existing}, "
                f"new_clusters={created_clusters}, skipped={skipped})"
            )

    info(
        "Assign complete: "
        f"joined={assigned_existing}, new_clusters={created_clusters}, skipped={skipped}"
    )

    session.flush()
    return {
        "assigned_existing": assigned_existing,
        "created_clusters": created_clusters,
        "skipped": skipped,
        "examined": len(articles),
    }


def mark_ready_clusters(
    session: Session, *, force: bool = False
) -> dict[str, int]:
    settings = get_settings()
    now = datetime.now(IST)
    cooldown = timedelta(minutes=settings.cluster_cooldown_minutes)

    clusters = list(
        session.scalars(
            select(StoryCluster).where(StoryCluster.status == ClusterStatus.OPEN)
        )
    )

    ready = 0
    for cluster in clusters:
        if force:
            cluster.status = ClusterStatus.READY_FOR_LLM
            ready += 1
            continue

        if cluster.last_published_at is None:
            continue

        last_seen = cluster.updated_at or cluster.last_published_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=IST)

        if now - last_seen >= cooldown and cluster.article_count >= 1:
            cluster.status = ClusterStatus.READY_FOR_LLM
            ready += 1

    if clusters:
        info(f"Marked {ready}/{len(clusters)} clusters ready_for_llm")

    session.flush()
    return {"ready": ready, "examined": len(clusters)}


def get_cluster_payload(session: Session, cluster_id) -> dict:
    cluster = session.get(
        StoryCluster,
        cluster_id,
        options=[joinedload(StoryCluster.articles)],
    )
    if cluster is None:
        raise ValueError(f"Cluster not found: {cluster_id}")

    articles = sorted(
        cluster.articles,
        key=lambda article: article.published_at or datetime.min.replace(
            tzinfo=IST
        ),
    )

    return {
        "cluster_id": str(cluster.id),
        "scope": cluster.scope,
        "status": cluster.status.value,
        "article_count": cluster.article_count,
        "articles": [
            {
                "source": article.source,
                "title": article.title,
                "url": article.url,
                "summary": article.summary,
                "body": article.body,
                "published_at": (
                    to_ist_iso(article.published_at) if article.published_at else None
                ),
            }
            for article in articles
        ],
    }
