import pytest

from clustering.ingest import _article_from_item, _parse_datetime


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
