from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from clustering.assigner import get_cluster_payload
from clustering.config import get_settings
from clustering.db.models import Article, ClusterStatus, StoryCluster
from clustering.db.publish_models import SynthesizedStory
from clustering.db.publish_session import get_publish_session
from clustering.db.session import get_session
from clustering.log import info
from clustering.synthesis.openrouter_client import OpenRouterClient, SynthesisError
from clustering.synthesis.prompt import SynthesisResult
from clustering.timezone_util import IST


def resolve_representative_article(
    cluster: StoryCluster, articles: list[Article]
) -> Article:
    if cluster.representative_article_id is not None:
        for article in articles:
            if article.id == cluster.representative_article_id:
                return article

    return min(
        articles,
        key=lambda article: (
            article.published_at or datetime.max.replace(tzinfo=IST),
            article.created_at,
        ),
    )


def build_synthesized_story(
    *,
    cluster: StoryCluster,
    articles: list[Article],
    result: SynthesisResult,
    synthesized_at: datetime,
) -> SynthesizedStory:
    representative = resolve_representative_article(cluster, articles)
    source_urls = [article.url for article in articles if article.url]
    sources = sorted(
        {article.source for article in articles if article.source}
    )

    return SynthesizedStory(
        cluster_id=cluster.id,
        title=result.title or "",
        summary=result.summary,
        body=result.body,
        url=representative.url,
        source=representative.source,
        author=representative.author,
        image=representative.image,
        tags=representative.tags,
        language=representative.language,
        scope=cluster.scope or representative.scope,
        published_at=representative.published_at,
        scraped_at=representative.scraped_at,
        source_urls=source_urls,
        sources=sources,
        synthesized_at=synthesized_at,
    )


def _claim_ready_clusters(
    session: Session, *, limit: int | None
) -> list[uuid.UUID]:
    stmt = (
        select(StoryCluster.id)
        .where(StoryCluster.status == ClusterStatus.READY_FOR_LLM)
        .order_by(StoryCluster.last_published_at.asc().nulls_last())
        .with_for_update(skip_locked=True)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.scalars(stmt))


def synthesize_clusters(
    *,
    limit: int | None = None,
    llm_client: OpenRouterClient | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise SystemExit(
            "OPENROUTER_API_KEY is required. Set it in clustering/.env and retry."
        )

    stats = {
        "examined": 0,
        "rewritten": 0,
        "dropped": 0,
        "failed": 0,
        "skipped_existing": 0,
    }

    owns_client = llm_client is None
    client = llm_client or OpenRouterClient()

    try:
        with get_session() as cluster_session:
            cluster_ids = _claim_ready_clusters(cluster_session, limit=limit)
            stats["examined"] = len(cluster_ids)

            if not cluster_ids:
                info("No ready_for_llm clusters to synthesize.")
                return stats

            info(f"Synthesizing {len(cluster_ids)} cluster(s) ...")

            for index, cluster_id in enumerate(cluster_ids, start=1):
                try:
                    outcome = _process_cluster(cluster_session, client, cluster_id)
                    stats[outcome] += 1
                except SynthesisError as exc:
                    stats["failed"] += 1
                    info(f"  cluster {cluster_id} failed: {exc}")
                    cluster_session.rollback()
                    continue

                if index % 10 == 0 or index == len(cluster_ids):
                    info(
                        f"  processed {index}/{len(cluster_ids)} "
                        f"(rewritten={stats['rewritten']}, "
                        f"dropped={stats['dropped']}, "
                        f"failed={stats['failed']})"
                    )
    finally:
        if owns_client:
            client.close()

    info(
        "Synthesis complete: "
        f"rewritten={stats['rewritten']}, dropped={stats['dropped']}, "
        f"failed={stats['failed']}, skipped_existing={stats['skipped_existing']}"
    )
    return stats


def _process_cluster(
    cluster_session: Session,
    client: OpenRouterClient,
    cluster_id: uuid.UUID,
) -> str:
    cluster = cluster_session.get(
        StoryCluster,
        cluster_id,
        options=[joinedload(StoryCluster.articles)],
    )
    if cluster is None:
        raise SynthesisError(f"Cluster not found: {cluster_id}")
    if cluster.status != ClusterStatus.READY_FOR_LLM:
        return "skipped_existing"

    payload = get_cluster_payload(cluster_session, cluster_id)
    result = client.synthesize_cluster(payload)
    synthesized_at = datetime.now(IST)

    if result.action == "drop":
        cluster.status = ClusterStatus.SYNTHESIZED
        cluster_session.commit()
        info(f"  dropped cluster {cluster_id}: {result.drop_reason}")
        return "dropped"

    story = build_synthesized_story(
        cluster=cluster,
        articles=cluster.articles,
        result=result,
        synthesized_at=synthesized_at,
    )

    with get_publish_session() as publish_session:
        existing = publish_session.scalar(
            select(SynthesizedStory).where(
                SynthesizedStory.cluster_id == cluster.id
            )
        )
        if existing is None:
            publish_session.add(story)
        publish_session.commit()

    cluster.status = ClusterStatus.SYNTHESIZED
    cluster_session.commit()
    info(f"  rewritten cluster {cluster_id}")
    return "rewritten"
