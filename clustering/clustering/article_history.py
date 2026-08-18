from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.orm import Session

from clustering.db.dropped_models import DroppedArticle
from clustering.db.publish_models import SynthesizedStory
from clustering.url_id import canonicalize_url, url_to_id
from clustering.timezone_util import IST


def find_known_urls(
    publish_session: Session,
    dropped_session: Session,
    urls: list[str],
) -> set[str]:
    """Return URLs already present in synthesized stories or dropped articles."""
    if not urls:
        return set()

    unique_urls = list(dict.fromkeys(urls))
    known: set[str] = set()

    dropped_ids = [url_to_id(url) for url in unique_urls]
    dropped_rows = dropped_session.scalars(
        select(DroppedArticle.url).where(DroppedArticle.id.in_(dropped_ids))
    ).all()
    known.update(dropped_rows)

    remaining = [url for url in unique_urls if url not in known]
    if not remaining:
        return known

    synthesized_rows = publish_session.scalars(
        select(SynthesizedStory.source_urls).where(
            SynthesizedStory.source_urls.op("?|")(array(remaining))
        )
    ).all()
    for source_urls in synthesized_rows:
        if not source_urls:
            continue
        for url in source_urls:
            if url in remaining:
                known.add(url)

    return known


def filter_cluster_payload(payload: dict, unseen_urls: set[str]) -> dict:
    articles = [
        article
        for article in payload.get("articles", [])
        if article.get("url") in unseen_urls
    ]
    return {
        **payload,
        "articles": articles,
        "article_count": len(articles),
    }


def persist_dropped_urls(
    dropped_session: Session,
    *,
    urls: list[str],
    cluster_id: uuid.UUID,
    drop_reason: str | None,
) -> None:
    dropped_at = datetime.now(IST)
    for url in urls:
        if not url:
            continue
        canonical = canonicalize_url(url)
        article_id = url_to_id(canonical)
        existing = dropped_session.get(DroppedArticle, article_id)
        if existing is None:
            dropped_session.add(
                DroppedArticle(
                    id=article_id,
                    url=url,
                    cluster_id=cluster_id,
                    drop_reason=drop_reason,
                    dropped_at=dropped_at,
                )
            )
        else:
            existing.url = url
            existing.cluster_id = cluster_id
            existing.drop_reason = drop_reason
            existing.dropped_at = dropped_at
