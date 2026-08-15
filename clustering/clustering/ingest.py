from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from clustering.db.models import Article, ArticleEmbedding
from clustering.log import info
from clustering.text import article_content_hash
from clustering.timezone_util import IST

URL_LOOKUP_CHUNK = 500
FLUSH_EVERY = 100

UpsertOutcome = Literal["created", "updated", "unchanged"]


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=IST)
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=IST)
        return parsed
    return None


def _article_from_item(item: dict[str, Any]) -> dict[str, Any]:
    url = item.get("url")
    if not url:
        raise ValueError("Article item missing required field: url")

    tags = item.get("tags")
    if tags is not None and not isinstance(tags, list):
        tags = [tags]

    title = item.get("title")
    summary = item.get("summary")
    body = item.get("body")

    return {
        "url": url,
        "title": title,
        "summary": summary,
        "body": body,
        "source": item.get("source"),
        "scope": item.get("scope"),
        "language": item.get("language"),
        "author": item.get("author"),
        "image": item.get("image"),
        "tags": tags,
        "published_at": _parse_datetime(item.get("published_at")),
        "scraped_at": _parse_datetime(item.get("scraped_at")),
        "content_hash": article_content_hash(title, summary, body),
    }


def _chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _load_existing_hashes(
    session: Session, urls: list[str]
) -> dict[str, tuple[uuid.UUID, str | None]]:
    if not urls:
        return {}

    existing: dict[str, tuple[uuid.UUID, str | None]] = {}
    for chunk in _chunked(urls, URL_LOOKUP_CHUNK):
        rows = session.execute(
            select(Article.id, Article.url, Article.content_hash).where(
                Article.url.in_(chunk)
            )
        )
        for article_id, url, content_hash in rows:
            existing[url] = (article_id, content_hash)
    return existing


def _invalidate_embedding(session: Session, article_id: uuid.UUID) -> None:
    session.execute(
        delete(ArticleEmbedding).where(ArticleEmbedding.article_id == article_id)
    )


def _touch_scraped_at(
    session: Session,
    article_id: uuid.UUID,
    scraped_at: datetime | None,
) -> None:
    if scraped_at is None:
        return
    session.execute(
        update(Article)
        .where(Article.id == article_id)
        .values(scraped_at=scraped_at)
    )


def _flush_scraped_at_touches(
    session: Session,
    touches: list[tuple[uuid.UUID, datetime]],
) -> None:
    for article_id, scraped_at in touches:
        _touch_scraped_at(session, article_id, scraped_at)


def upsert_article(session: Session, item: dict[str, Any]) -> tuple[Article, UpsertOutcome]:
    data = _article_from_item(item)
    existing = session.scalar(select(Article).where(Article.url == data["url"]))

    if existing is None:
        article = Article(**data)
        session.add(article)
        session.flush()
        return article, "created"

    if existing.content_hash == data["content_hash"]:
        if data["scraped_at"] is not None:
            existing.scraped_at = data["scraped_at"]
            session.flush()
        return existing, "unchanged"

    for field, value in data.items():
        setattr(existing, field, value)
    _invalidate_embedding(session, existing.id)
    session.flush()
    return existing, "updated"


def ingest_json_file(session: Session, path: str | Path) -> dict[str, int]:
    file_path = Path(path)
    info(f"Reading {file_path} ...")
    with file_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        raise ValueError("Expected JSON array of BytezItem objects")

    parsed_items: list[dict[str, Any]] = []
    skipped = 0
    for item in payload:
        if not isinstance(item, dict):
            skipped += 1
            continue
        try:
            parsed_items.append(_article_from_item(item))
        except ValueError:
            skipped += 1

    total = len(payload)
    info(f"Ingesting {total} articles ({len(parsed_items)} valid) ...")

    urls = [item["url"] for item in parsed_items]
    existing_by_url = _load_existing_hashes(session, urls)

    created = 0
    updated = 0
    unchanged = 0
    pending_writes = 0
    scraped_at_touches: list[tuple[uuid.UUID, datetime]] = []
    pending_by_url: dict[str, tuple[Article, str]] = {}

    for index, data in enumerate(parsed_items, start=1):
        url = data["url"]
        pending = pending_by_url.get(url)
        if pending is not None:
            article, stored_hash = pending
            if stored_hash == data["content_hash"]:
                unchanged += 1
                if data["scraped_at"] is not None:
                    article.scraped_at = data["scraped_at"]
                    pending_writes += 1
            else:
                for field, value in data.items():
                    setattr(article, field, value)
                pending_by_url[url] = (article, data["content_hash"])
                updated += 1
                pending_writes += 1
            continue

        existing = existing_by_url.get(url)

        if existing is None:
            article = Article(**data)
            session.add(article)
            pending_by_url[url] = (article, data["content_hash"])
            created += 1
            pending_writes += 1
        else:
            article_id, stored_hash = existing
            if stored_hash == data["content_hash"]:
                unchanged += 1
                if data["scraped_at"] is not None:
                    scraped_at_touches.append((article_id, data["scraped_at"]))
                continue

            article = session.get(Article, article_id)
            if article is None:
                skipped += 1
                continue

            for field, value in data.items():
                setattr(article, field, value)
            _invalidate_embedding(session, article_id)
            existing_by_url[url] = (article_id, data["content_hash"])
            updated += 1
            pending_writes += 1

        if pending_writes >= FLUSH_EVERY:
            session.flush()
            for pending_url, (pending_article, pending_hash) in pending_by_url.items():
                if pending_article.id is not None:
                    existing_by_url[pending_url] = (pending_article.id, pending_hash)
            pending_writes = 0

        if len(scraped_at_touches) >= FLUSH_EVERY:
            _flush_scraped_at_touches(session, scraped_at_touches)
            scraped_at_touches.clear()

        if index % 100 == 0 or index == len(parsed_items):
            info(
                f"  processed {index}/{len(parsed_items)} "
                f"(created={created}, updated={updated}, "
                f"unchanged={unchanged}, skipped={skipped})"
            )

    if pending_writes:
        session.flush()
        for pending_url, (pending_article, pending_hash) in pending_by_url.items():
            if pending_article.id is not None:
                existing_by_url[pending_url] = (pending_article.id, pending_hash)

    if scraped_at_touches:
        _flush_scraped_at_touches(session, scraped_at_touches)

    info(
        "Ingest complete: "
        f"created={created}, updated={updated}, "
        f"unchanged={unchanged}, skipped={skipped}"
    )
    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "skipped": skipped,
    }
