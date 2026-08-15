import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from clustering.db.models import Article, ClusterStatus, StoryCluster
from clustering.synthesis.prompt import SynthesisResult
from clustering.synthesis.worker import (
    build_synthesized_story,
    resolve_representative_article,
    synthesize_clusters,
)


def _article(
    *,
    url: str,
    source: str,
    published_at: datetime,
    title: str = "Title",
) -> Article:
    return Article(
        id=uuid.uuid4(),
        url=url,
        title=title,
        summary="Summary",
        body="Body",
        source=source,
        scope="India",
        author="Author",
        image="https://example.com/image.jpg",
        tags=["politics"],
        language="en",
        published_at=published_at,
        scraped_at=published_at,
    )


def test_resolve_representative_article_prefers_cluster_representative():
    earlier = _article(
        url="https://example.com/a",
        source="The Hindu",
        published_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )
    later = _article(
        url="https://example.com/b",
        source="TOI",
        published_at=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
    )
    cluster = StoryCluster(representative_article_id=later.id)
    representative = resolve_representative_article(cluster, [earlier, later])
    assert representative.id == later.id


def test_resolve_representative_article_falls_back_to_earliest_published():
    earlier = _article(
        url="https://example.com/a",
        source="The Hindu",
        published_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )
    later = _article(
        url="https://example.com/b",
        source="TOI",
        published_at=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
    )
    cluster = StoryCluster(representative_article_id=None)
    representative = resolve_representative_article(cluster, [later, earlier])
    assert representative.id == earlier.id


def test_build_synthesized_story_merges_clone_and_rewrite_fields():
    article = _article(
        url="https://example.com/a",
        source="The Hindu",
        published_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )
    other = _article(
        url="https://example.com/b",
        source="TOI",
        published_at=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
    )
    cluster = StoryCluster(
        id=uuid.uuid4(),
        representative_article_id=article.id,
        scope="India",
    )
    synthesized_at = datetime(2026, 8, 5, 13, 0, tzinfo=timezone.utc)
    result = SynthesisResult(
        action="rewrite",
        drop_reason=None,
        scope="Tamil Nadu",
        priority=82,
        title="Rewritten title",
        summary="Rewritten summary",
        body="Rewritten body",
    )

    story = build_synthesized_story(
        cluster=cluster,
        articles=[article, other],
        result=result,
        synthesized_at=synthesized_at,
    )

    assert story.title == "Rewritten title"
    assert story.slug
    assert story.summary == "Rewritten summary"
    assert story.body == "Rewritten body"
    assert story.url == article.url
    assert story.author == article.author
    assert story.image == article.image
    assert story.tags == article.tags
    assert story.language == article.language
    assert story.scope == "Tamil Nadu"
    assert story.priority == 82
    assert story.source_urls == [article.url, other.url]
    assert story.sources == ["TOI", "The Hindu"]
    assert story.synthesized_at == synthesized_at


@patch("clustering.synthesis.worker.get_publish_session")
@patch("clustering.synthesis.worker.get_session")
def test_synthesize_clusters_drop_skips_publish(get_session_mock, get_publish_mock, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    from clustering.config import get_settings

    get_settings.cache_clear()
    cluster_id = uuid.uuid4()
    article = _article(
        url="https://example.com/a",
        source="The Hindu",
        published_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )
    cluster = StoryCluster(
        id=cluster_id,
        representative_article_id=article.id,
        scope="India",
        status=ClusterStatus.READY_FOR_LLM,
        articles=[article],
    )

    cluster_session = MagicMock()
    cluster_session.scalars.return_value.all.return_value = [cluster_id]
    cluster_session.get.return_value = cluster
    get_session_mock.return_value.__enter__.return_value = cluster_session

    publish_session = MagicMock()
    publish_session.scalar.return_value = None
    get_publish_mock.return_value.__enter__.return_value = publish_session

    mock_client = MagicMock()
    mock_client.synthesize_cluster.return_value = SynthesisResult(
        action="drop",
        drop_reason="Sports highlight",
        scope=None,
        priority=None,
        title=None,
        summary=None,
        body=None,
    )

    stats = synthesize_clusters(limit=1, llm_client=mock_client)

    assert stats["dropped"] == 1
    assert stats["rewritten"] == 0
    publish_session.add.assert_not_called()
    assert cluster.status == ClusterStatus.SYNTHESIZED
