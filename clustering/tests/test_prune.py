from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from clustering.prune import (
    BYTES_PER_MB,
    _cutoff,
    _should_prune,
    prune_all_databases,
    prune_publish_database,
)


def test_cutoff_uses_retention_days():
    cutoff = _cutoff(10)
    now = datetime.now(cutoff.tzinfo)
    delta = now - cutoff
    assert 9 <= delta.days <= 10


def test_should_prune_when_at_limit():
    session = MagicMock()
    settings = MagicMock()
    settings.db_size_limit_mb = 475
    limit_bytes = 475 * BYTES_PER_MB

    with patch("clustering.prune.get_settings", return_value=settings):
        with patch(
            "clustering.prune._database_size_bytes",
            return_value=limit_bytes,
        ):
            should_prune, size = _should_prune(session)

    assert should_prune is True
    assert size == limit_bytes


def test_should_prune_skips_under_limit():
    session = MagicMock()
    settings = MagicMock()
    settings.db_size_limit_mb = 475

    with patch("clustering.prune.get_settings", return_value=settings):
        with patch(
            "clustering.prune._database_size_bytes",
            return_value=100 * BYTES_PER_MB,
        ):
            should_prune, _size = _should_prune(session)

    assert should_prune is False


def test_prune_publish_skips_when_under_limit():
    session = MagicMock()

    with patch("clustering.prune.get_publish_session") as mock_ctx:
        mock_ctx.return_value.__enter__.return_value = session
        with patch("clustering.prune._should_prune", return_value=(False, 100)):
            stats = prune_publish_database()

    assert stats["pruned"] is False
    assert stats["stories_deleted"] == 0
    session.execute.assert_not_called()


def test_prune_publish_writes_redirects_and_deletes_old_stories():
    session = MagicMock()
    old_id = uuid.uuid4()
    story = MagicMock()
    story.id = old_id
    story.slug = "old-story"
    story.scope = "Chennai"
    story.url = "https://publisher.example/article"

    session.scalars.return_value.all.return_value = [story]

    with patch("clustering.prune.get_settings") as mock_settings:
        mock_settings.return_value.retention_days = 10
        with patch("clustering.prune.get_publish_session") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = session
            with patch("clustering.prune._should_prune", return_value=(True, 500)):
                with patch("clustering.prune._cutoff") as mock_cutoff:
                    mock_cutoff.return_value = datetime.now(timezone.utc) - timedelta(
                        days=11
                    )
                    stats = prune_publish_database()

    assert stats["pruned"] is True
    assert stats["redirects_written"] == 1
    assert stats["stories_deleted"] == 1
    assert session.execute.call_count >= 3


def test_prune_all_reports_each_database():
    publish_stats = {"pruned": False, "size_mb": 10}
    clustering_stats = {"pruned": False, "size_mb": 20}
    dropped_stats = {"pruned": False, "size_mb": 5}
    feedback_stats = {"skipped": True}

    with patch("clustering.prune.prune_publish_database", return_value=publish_stats):
        with patch(
            "clustering.prune.prune_clustering_database",
            return_value=clustering_stats,
        ):
            with patch(
                "clustering.prune.prune_dropped_database",
                return_value=dropped_stats,
            ):
                with patch(
                    "clustering.prune.prune_feedback_database",
                    return_value=feedback_stats,
                ):
                    results = prune_all_databases()

    assert results == {
        "publish": publish_stats,
        "clustering": clustering_stats,
        "dropped": dropped_stats,
        "feedback": feedback_stats,
    }
