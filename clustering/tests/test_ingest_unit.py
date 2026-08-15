import pytest
from unittest.mock import MagicMock

from clustering.ingest import _article_from_item, _parse_datetime, upsert_article
from clustering.text import article_content_hash


def test_parse_datetime_handles_z_suffix():
    parsed = _parse_datetime("2026-08-05T10:00:00Z")
    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.utcoffset().total_seconds() == 0


def test_article_from_item_requires_url():
    with pytest.raises(ValueError, match="url"):
        _article_from_item({"title": "No URL"})


def test_article_from_item_normalizes_tags():
    data = _article_from_item(
        {
            "url": "https://example.com/a",
            "title": "Title",
            "tags": "politics",
        }
    )
    assert data["tags"] == ["politics"]


def test_article_from_item_includes_content_hash():
    data = _article_from_item(
        {
            "url": "https://example.com/a",
            "title": "Title",
            "summary": "Summary",
            "body": "Body",
        }
    )
    assert data["content_hash"] == article_content_hash("Title", "Summary", "Body")


def test_upsert_article_touches_scraped_at_when_unchanged():
    session = MagicMock()
    existing = MagicMock()
    existing.content_hash = article_content_hash("Title", None, None)
    session.scalar.return_value = existing

    item = {
        "url": "https://example.com/a",
        "title": "Title",
        "scraped_at": "2026-08-15T10:00:00+00:00",
    }
    article, outcome = upsert_article(session, item)

    assert outcome == "unchanged"
    assert article is existing
    assert existing.scraped_at is not None
    session.flush.assert_called_once()


def test_upsert_article_skips_unchanged_without_scraped_at():
    session = MagicMock()
    existing = MagicMock()
    existing.content_hash = article_content_hash("Title", None, None)
    session.scalar.return_value = existing

    item = {
        "url": "https://example.com/a",
        "title": "Title",
    }
    article, outcome = upsert_article(session, item)

    assert outcome == "unchanged"
    assert article is existing
    session.flush.assert_not_called()


def test_upsert_article_updates_when_hash_changes():
    session = MagicMock()
    existing = MagicMock()
    existing.id = "article-id"
    existing.content_hash = "old-hash"
    session.scalar.return_value = existing

    item = {
        "url": "https://example.com/a",
        "title": "New title",
    }
    _, outcome = upsert_article(session, item)

    assert outcome == "updated"
    session.execute.assert_called_once()
    session.flush.assert_called_once()
