from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from clustering.db.models import Article
from clustering.log import info
from clustering.timezone_util import IST


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

    return {
        "url": url,
        "title": item.get("title"),
        "summary": item.get("summary"),
        "body": item.get("body"),
        "source": item.get("source"),
        "scope": item.get("scope"),
        "language": item.get("language"),
        "author": item.get("author"),
        "image": item.get("image"),
        "tags": tags,
        "published_at": _parse_datetime(item.get("published_at")),
        "scraped_at": _parse_datetime(item.get("scraped_at")),
    }


def upsert_article(session: Session, item: dict[str, Any]) -> tuple[Article, bool]:
    data = _article_from_item(item)
    existing = session.scalar(select(Article).where(Article.url == data["url"]))

    if existing is None:
        article = Article(**data)
        session.add(article)
        session.flush()
        return article, True

    for field, value in data.items():
        setattr(existing, field, value)
    session.flush()
    return existing, False


def ingest_json_file(session: Session, path: str | Path) -> dict[str, int]:
    file_path = Path(path)
    info(f"Reading {file_path} ...")
    with file_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        raise ValueError("Expected JSON array of BytezItem objects")

    total = len(payload)
    info(f"Ingesting {total} articles ...")

    created = 0
    updated = 0
    skipped = 0

    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            skipped += 1
            continue
        try:
            _, is_new = upsert_article(session, item)
        except ValueError:
            skipped += 1
            continue
        if is_new:
            created += 1
        else:
            updated += 1

        if index % 100 == 0 or index == total:
            info(
                f"  processed {index}/{total} "
                f"(created={created}, updated={updated}, skipped={skipped})"
            )

    info(
        f"Ingest complete: created={created}, updated={updated}, skipped={skipped}"
    )
    return {"created": created, "updated": updated, "skipped": skipped}
