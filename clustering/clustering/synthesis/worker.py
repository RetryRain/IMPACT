from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from clustering.article_history import (
    filter_cluster_payload,
    find_known_urls,
    persist_dropped_urls,
)
from clustering.assigner import get_cluster_payload
from clustering.config import get_settings
from clustering.db.models import Article, ClusterStatus, StoryCluster
from clustering.db.dropped_session import get_dropped_session
from clustering.db.publish_models import SynthesizedStory
from clustering.db.publish_session import get_publish_session
from clustering.db.session import get_session
from clustering.log import info
from clustering.publishers import publisher_image_rank
from clustering.synthesis.client import get_synthesis_client, SynthesisClient
from clustering.synthesis.llm_client import SynthesisError
from clustering.synthesis.prompt import SynthesisResult
from clustering.synthesis.run_log import SynthesisRunLog
from clustering.slug import make_story_slug
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


def resolve_article_image(articles: list[Article], fallback: Article) -> str | None:
    """Pick image from highest-ranked publisher that has one (IE > TOI > Hindu)."""
    candidates = [
        article
        for article in articles
        if article.image and str(article.image).strip()
    ]
    if not candidates:
        return fallback.image

    def sort_key(article: Article) -> tuple[int, float]:
        rank = publisher_image_rank(article.source, article.url)
        published_ts = (
            article.published_at.timestamp()
            if article.published_at is not None
            else 0.0
        )
        return (rank, -published_ts)

    best = max(candidates, key=sort_key)
    return best.image


def union_article_tags(articles: list[Article]) -> list[str] | None:
    seen: set[str] = set()
    tags: list[str] = []
    for article in articles:
        if not article.tags:
            continue
        for tag in article.tags:
            if not isinstance(tag, str):
                continue
            normalized = tag.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                tags.append(normalized)
    return tags or None


def build_synthesized_story(
    *,
    cluster: StoryCluster,
    articles: list[Article],
    result: SynthesisResult,
    synthesized_at: datetime,
    story_id: uuid.UUID | None = None,
) -> SynthesizedStory:
    representative = resolve_representative_article(cluster, articles)
    image = resolve_article_image(articles, representative)
    source_urls = [article.url for article in articles if article.url]
    sources = sorted(
        {article.source for article in articles if article.source}
    )

    resolved_id = story_id or uuid.uuid4()
    return SynthesizedStory(
        id=resolved_id,
        cluster_id=cluster.id,
        title=result.title or "",
        slug=make_story_slug(result.title or "story", resolved_id),
        summary=result.summary,
        body=result.body,
        url=representative.url,
        source=representative.source,
        author=representative.author,
        image=image,
        tags=union_article_tags(articles),
        language=representative.language,
        scope=result.scope,
        priority=result.priority or 0,
        published_at=representative.published_at,
        scraped_at=representative.scraped_at,
        source_urls=source_urls,
        sources=sources,
        synthesized_at=synthesized_at,
    )


def apply_synthesis_result_to_story(
    existing: SynthesizedStory,
    *,
    cluster: StoryCluster,
    articles: list[Article],
    result: SynthesisResult,
    synthesized_at: datetime,
) -> SynthesizedStory:
    representative = resolve_representative_article(cluster, articles)
    image = resolve_article_image(articles, representative)
    source_urls = [article.url for article in articles if article.url]
    sources = sorted({article.source for article in articles if article.source})

    existing.title = result.title or ""
    existing.summary = result.summary
    existing.body = result.body
    existing.url = representative.url
    existing.source = representative.source
    existing.author = representative.author
    existing.image = image
    existing.tags = union_article_tags(articles)
    existing.language = representative.language
    existing.scope = result.scope
    existing.priority = result.priority or 0
    existing.published_at = representative.published_at
    existing.scraped_at = representative.scraped_at
    existing.source_urls = source_urls
    existing.sources = sources
    existing.synthesized_at = synthesized_at
    return existing


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
    llm_client: SynthesisClient | None = None,
    run_log: SynthesisRunLog | None = None,
) -> dict[str, Any]:
    stats = {
        "examined": 0,
        "rewritten": 0,
        "dropped": 0,
        "failed": 0,
        "skipped_existing": 0,
    }

    log = run_log or SynthesisRunLog()
    run_started = time.perf_counter()

    with get_session() as cluster_session:
        cluster_ids = _claim_ready_clusters(cluster_session, limit=limit)
        stats["examined"] = len(cluster_ids)

    if not cluster_ids:
        info("No ready_for_llm clusters to synthesize.")
        log.log_summary(
            stats,
            duration_ms=0,
            concurrency=max(1, get_settings().synthesis_concurrency),
            limit=limit,
        )
        info(f"Synthesis log: {log.path}")
        return stats

    concurrency = max(1, get_settings().synthesis_concurrency)
    info(f"Synthesizing {len(cluster_ids)} cluster(s) (concurrency={concurrency}) ...")

    shared_client = llm_client is not None

    def process_one(cluster_id: uuid.UUID) -> str:
        client = llm_client or get_synthesis_client()
        try:
            with get_session() as cluster_session:
                try:
                    return _process_cluster(
                        cluster_session,
                        client,
                        cluster_id,
                        run_log=log,
                    )
                except SynthesisError as exc:
                    info(f"  cluster {cluster_id} failed: {exc}")
                    cluster_session.rollback()
                    log.log_cluster(
                        cluster_id=str(cluster_id),
                        outcome="failed",
                        error=str(exc),
                    )
                    return "failed"
        finally:
            if not shared_client:
                client.close()

    if concurrency <= 1:
        for index, cluster_id in enumerate(cluster_ids, start=1):
            outcome = process_one(cluster_id)
            stats[outcome] += 1
            if index % 10 == 0 or index == len(cluster_ids):
                info(
                    f"  processed {index}/{len(cluster_ids)} "
                    f"(rewritten={stats['rewritten']}, "
                    f"dropped={stats['dropped']}, "
                    f"failed={stats['failed']})"
                )
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(process_one, cluster_id): cluster_id
                for cluster_id in cluster_ids
            }
            for index, future in enumerate(as_completed(futures), start=1):
                outcome = future.result()
                stats[outcome] += 1
                if index % 10 == 0 or index == len(cluster_ids):
                    info(
                        f"  processed {index}/{len(cluster_ids)} "
                        f"(rewritten={stats['rewritten']}, "
                        f"dropped={stats['dropped']}, "
                        f"failed={stats['failed']})"
                    )

    duration_ms = int((time.perf_counter() - run_started) * 1000)
    log.log_summary(
        stats,
        duration_ms=duration_ms,
        concurrency=concurrency,
        limit=limit,
    )

    info(
        "Synthesis complete: "
        f"rewritten={stats['rewritten']}, dropped={stats['dropped']}, "
        f"failed={stats['failed']}, skipped_existing={stats['skipped_existing']}"
    )
    info(f"Synthesis log: {log.path}")
    return stats


def _cluster_log_context(
    cluster: StoryCluster,
    articles: list[Article],
) -> dict[str, Any]:
    sources = sorted({article.source for article in articles if article.source})
    source_urls = [article.url for article in articles if article.url]
    return {
        "cluster_id": str(cluster.id),
        "assigned_scope": cluster.scope,
        "article_count": len(articles),
        "sources": sources,
        "source_urls": source_urls,
    }


def _process_cluster(
    cluster_session: Session,
    client: SynthesisClient,
    cluster_id: uuid.UUID,
    *,
    run_log: SynthesisRunLog | None = None,
) -> str:
    started = time.perf_counter()
    cluster = cluster_session.get(
        StoryCluster,
        cluster_id,
        options=[joinedload(StoryCluster.articles)],
    )
    if cluster is None:
        raise SynthesisError(f"Cluster not found: {cluster_id}")
    if cluster.status != ClusterStatus.READY_FOR_LLM:
        if run_log is not None:
            run_log.log_cluster(
                cluster_id=str(cluster_id),
                outcome="skipped_existing",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        return "skipped_existing"

    articles = cluster.articles
    context = _cluster_log_context(cluster, articles)
    article_urls = [article.url for article in articles if article.url]

    payload = get_cluster_payload(cluster_session, cluster_id)

    with get_publish_session() as publish_session, get_dropped_session() as dropped_session:
        known_urls = find_known_urls(publish_session, dropped_session, article_urls)
        unseen_urls = {url for url in article_urls if url not in known_urls}

        if not unseen_urls:
            cluster.status = ClusterStatus.SYNTHESIZED
            cluster_session.commit()
            duration_ms = int((time.perf_counter() - started) * 1000)
            info(
                f"  skipped cluster {cluster_id}: all {len(article_urls)} "
                "source URL(s) already processed"
            )
            if run_log is not None:
                run_log.log_cluster(
                    **context,
                    outcome="skipped_existing",
                    known_url_count=len(known_urls),
                    duration_ms=duration_ms,
                )
            return "skipped_existing"

        filtered_payload = filter_cluster_payload(payload, unseen_urls)

        classify_result = client.classify_cluster(filtered_payload)
        if classify_result.action == "drop":
            duration_ms = int((time.perf_counter() - started) * 1000)
            persist_dropped_urls(
                dropped_session,
                urls=article_urls,
                cluster_id=cluster_id,
                drop_reason=classify_result.drop_reason,
            )
            dropped_session.commit()
            cluster.status = ClusterStatus.SYNTHESIZED
            cluster_session.commit()
            info(f"  dropped cluster {cluster_id}: {classify_result.drop_reason}")
            if run_log is not None:
                run_log.log_cluster(
                    **context,
                    outcome="dropped",
                    action=classify_result.action,
                    drop_reason=classify_result.drop_reason,
                    known_url_count=len(known_urls),
                    duration_ms=duration_ms,
                )
            return "dropped"

        result = client.synthesize_cluster(filtered_payload)
        synthesized_at = datetime.now(IST)
        duration_ms = int((time.perf_counter() - started) * 1000)

        if result.action == "drop":
            persist_dropped_urls(
                dropped_session,
                urls=article_urls,
                cluster_id=cluster_id,
                drop_reason=result.drop_reason,
            )
            dropped_session.commit()
            cluster.status = ClusterStatus.SYNTHESIZED
            cluster_session.commit()
            info(
                f"  dropped cluster {cluster_id} after rewrite review: "
                f"{result.drop_reason}"
            )
            if run_log is not None:
                run_log.log_cluster(
                    **context,
                    outcome="dropped",
                    action=result.action,
                    drop_reason=result.drop_reason,
                    known_url_count=len(known_urls),
                    duration_ms=duration_ms,
                )
            return "dropped"

        story = build_synthesized_story(
            cluster=cluster,
            articles=articles,
            result=result,
            synthesized_at=synthesized_at,
        )

        published_new = False
        updated_existing = False
        existing = publish_session.scalar(
            select(SynthesizedStory).where(
                SynthesizedStory.cluster_id == cluster.id
            )
        )
        if existing is None:
            publish_session.add(story)
            published_new = True
        else:
            apply_synthesis_result_to_story(
                existing,
                cluster=cluster,
                articles=articles,
                result=result,
                synthesized_at=synthesized_at,
            )
            story = existing
            updated_existing = True
        publish_session.commit()

    cluster.status = ClusterStatus.SYNTHESIZED
    cluster_session.commit()
    info(f"  rewritten cluster {cluster_id}")
    if run_log is not None:
        run_log.log_cluster(
            **context,
            outcome="rewritten",
            action=result.action,
            scope=result.scope,
            priority=result.priority,
            title=result.title,
            summary=result.summary,
            story_id=str(story.id),
            slug=story.slug,
            tags=story.tags,
            published_new=published_new,
            updated_existing=updated_existing,
            known_url_count=len(known_urls),
            duration_ms=duration_ms,
        )
    return "rewritten"
