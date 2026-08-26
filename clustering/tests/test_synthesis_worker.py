import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from clustering.db.models import Article, ClusterStatus, StoryCluster
from clustering.synthesis.prompt import SynthesisResult
from clustering.synthesis.worker import (
    apply_synthesis_result_to_story,
    build_synthesized_story,
    resolve_article_image,
    resolve_representative_article,
    synthesize_clusters,
)


def _article(
    *,
    url: str,
    source: str,
    published_at: datetime,
    title: str = "Title",
    image: str = "https://example.com/image.jpg",
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
        image=image,
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


def test_resolve_article_image_prefers_indian_express_over_toi_and_hindu():
    hindu = _article(
        url="https://www.thehindu.com/a",
        source="The Hindu",
        published_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
        image="https://example.com/hindu.jpg",
    )
    toi = _article(
        url="https://timesofindia.indiatimes.com/b",
        source="The Times of India",
        published_at=datetime(2026, 8, 5, 11, 0, tzinfo=timezone.utc),
        image="https://example.com/toi.jpg",
    )
    ie = _article(
        url="https://indianexpress.com/c",
        source="The Indian Express",
        published_at=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
        image="https://example.com/ie.jpg",
    )

    image = resolve_article_image([hindu, toi, ie], hindu)
    assert image == "https://example.com/ie.jpg"


def test_resolve_article_image_prefers_toi_over_hindu():
    hindu = _article(
        url="https://www.thehindu.com/a",
        source="The Hindu",
        published_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
        image="https://example.com/hindu.jpg",
    )
    toi = _article(
        url="https://timesofindia.indiatimes.com/b",
        source="TOI",
        published_at=datetime(2026, 8, 5, 11, 0, tzinfo=timezone.utc),
        image="https://example.com/toi.jpg",
    )

    image = resolve_article_image([hindu, toi], hindu)
    assert image == "https://example.com/toi.jpg"


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
        image="https://example.com/toi.jpg",
    )
    other.tags = ["economy"]
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
        category="politics",
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
    assert story.image == "https://example.com/toi.jpg"
    assert story.tags == ["politics", "economy"]
    assert story.language == article.language
    assert story.scope == "Tamil Nadu"
    assert story.category == "politics"
    assert story.priority == 82
    assert story.source_urls == [article.url, other.url]
    assert story.sources == ["TOI", "The Hindu"]
    assert story.synthesized_at == synthesized_at


def test_apply_synthesis_result_to_story_updates_existing_row():
    article = _article(
        url="https://example.com/a",
        source="The Hindu",
        published_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
    )
    cluster = StoryCluster(
        id=uuid.uuid4(),
        representative_article_id=article.id,
        scope="India",
    )
    synthesized_at = datetime(2026, 8, 5, 13, 0, tzinfo=timezone.utc)
    existing = build_synthesized_story(
        cluster=cluster,
        articles=[article],
        result=SynthesisResult(
            action="rewrite",
            drop_reason=None,
            scope="India",
            category="economy",
            priority=50,
            title="Old title",
            summary="Old summary",
            body="Old body",
        ),
        synthesized_at=synthesized_at,
        story_id=uuid.uuid4(),
    )
    result = SynthesisResult(
        action="rewrite",
        drop_reason=None,
        scope="Tamil Nadu",
        category="politics",
        priority=82,
        title="Updated title",
        summary="Updated summary",
        body="Updated body",
    )
    updated = apply_synthesis_result_to_story(
        existing,
        cluster=cluster,
        articles=[article],
        result=result,
        synthesized_at=synthesized_at,
    )
    assert updated.id == existing.id
    assert updated.slug == existing.slug
    assert updated.title == "Updated title"
    assert updated.scope == "Tamil Nadu"
    assert updated.priority == 82


@patch("clustering.synthesis.worker.get_dropped_session")
@patch("clustering.synthesis.worker.get_publish_session")
@patch("clustering.synthesis.worker.get_session")
def test_synthesize_clusters_keep_calls_classify_then_rewrite(
    get_session_mock, get_publish_mock, get_dropped_mock, monkeypatch
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    from clustering.config import get_settings
    from clustering.synthesis.prompt import ClassifyResult, SynthesisResult

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

    dropped_session = MagicMock()
    get_dropped_mock.return_value.__enter__.return_value = dropped_session

    with patch(
        "clustering.synthesis.worker.find_known_urls", return_value=set()
    ):
        mock_client = MagicMock()
        mock_client.classify_cluster.return_value = ClassifyResult(
            action="keep",
            drop_reason=None,
        )
        mock_client.synthesize_cluster.return_value = SynthesisResult(
            action="rewrite",
            drop_reason=None,
            scope="India",
            category="politics",
            priority=70,
            title="Rewritten",
            summary="Summary",
            body="Body",
        )

        stats = synthesize_clusters(limit=1, llm_client=mock_client)

    assert stats["rewritten"] == 1
    mock_client.classify_cluster.assert_called_once()
    mock_client.synthesize_cluster.assert_called_once()
    publish_session.add.assert_called()


@patch("clustering.synthesis.worker.get_dropped_session")
@patch("clustering.synthesis.worker.get_publish_session")
@patch("clustering.synthesis.worker.get_session")
def test_synthesize_clusters_drop_skips_publish(
    get_session_mock, get_publish_mock, get_dropped_mock, monkeypatch
):
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

    dropped_session = MagicMock()
    get_dropped_mock.return_value.__enter__.return_value = dropped_session

    with patch(
        "clustering.synthesis.worker.find_known_urls", return_value=set()
    ):
        mock_client = MagicMock()
        from clustering.synthesis.prompt import ClassifyResult

        mock_client.classify_cluster.return_value = ClassifyResult(
            action="drop",
            drop_reason="Sports highlight",
        )

        stats = synthesize_clusters(limit=1, llm_client=mock_client)

    assert stats["dropped"] == 1
    assert stats["rewritten"] == 0
    mock_client.classify_cluster.assert_called_once()
    mock_client.synthesize_cluster.assert_not_called()
    publish_session.add.assert_not_called()
    dropped_session.add.assert_called()
    assert cluster.status == ClusterStatus.SYNTHESIZED


@patch("clustering.synthesis.worker.get_dropped_session")
@patch("clustering.synthesis.worker.get_publish_session")
@patch("clustering.synthesis.worker.get_session")
def test_synthesize_clusters_skips_when_all_urls_known(
    get_session_mock, get_publish_mock, get_dropped_mock, monkeypatch
):
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
    get_publish_mock.return_value.__enter__.return_value = publish_session
    dropped_session = MagicMock()
    get_dropped_mock.return_value.__enter__.return_value = dropped_session

    mock_client = MagicMock()
    with patch(
        "clustering.synthesis.worker.find_known_urls",
        return_value={"https://example.com/a"},
    ):
        stats = synthesize_clusters(limit=1, llm_client=mock_client)

    assert stats["skipped_existing"] == 1
    mock_client.classify_cluster.assert_not_called()
    mock_client.synthesize_cluster.assert_not_called()
    assert cluster.status == ClusterStatus.SYNTHESIZED
