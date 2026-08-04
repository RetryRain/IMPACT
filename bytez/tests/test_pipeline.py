from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from scrapy.exceptions import DropItem

from bytez.items import BytezItem
from bytez.pipelines import AgeFilterPipeline, BytezPipeline
from bytez.spiders.common import SpiderLimits


class TestAgeFilterPipeline:
    def test_drops_stale_and_missing_published_at(self):
        pipeline = AgeFilterPipeline()
        spider = MagicMock()
        spider.limits = SpiderLimits(
            max_total_articles=100,
            old_article_max_age=timedelta(days=1),
            max_old_article_ratio=0.5,
            min_articles_before_ratio_check=0,
            max_published_age_hours=24,
        )
        pipeline.open_spider(spider)

        stale = BytezItem(
            title="Stale",
            url="https://example.com/stale",
            published_at=(datetime.now(UTC) - timedelta(days=2)).isoformat(),
            scope="India",
            source="Example",
            language="en",
            scraped_at="2024-01-01T00:00:00+00:00",
        )
        with pytest.raises(DropItem):
            pipeline.process_item(stale, spider)

        missing = BytezItem(
            title="No date",
            url="https://example.com/no-date",
            scope="India",
            source="Example",
            language="en",
            scraped_at="2024-01-01T00:00:00+00:00",
        )
        with pytest.raises(DropItem):
            pipeline.process_item(missing, spider)

    def test_allows_recent_article(self):
        pipeline = AgeFilterPipeline()
        spider = MagicMock()
        spider.limits = SpiderLimits(
            max_total_articles=100,
            old_article_max_age=timedelta(days=1),
            max_old_article_ratio=0.5,
            min_articles_before_ratio_check=0,
            max_published_age_hours=24,
        )
        pipeline.open_spider(spider)

        fresh = BytezItem(
            title="Fresh",
            url="https://example.com/fresh",
            published_at=datetime.now(UTC).isoformat(),
            scope="India",
            source="Example",
            language="en",
            scraped_at="2024-01-01T00:00:00+00:00",
        )
        assert pipeline.process_item(fresh, spider) is fresh

    def test_disabled_when_max_published_age_hours_is_zero(self):
        pipeline = AgeFilterPipeline()
        spider = MagicMock()
        spider.limits = SpiderLimits(
            max_total_articles=100,
            old_article_max_age=timedelta(days=1),
            max_old_article_ratio=0.5,
            min_articles_before_ratio_check=0,
            max_published_age_hours=0,
        )
        pipeline.open_spider(spider)

        stale = BytezItem(
            title="Stale",
            url="https://example.com/stale-legacy",
            published_at=(datetime.now(UTC) - timedelta(days=2)).isoformat(),
            scope="India",
            source="Example",
            language="en",
            scraped_at="2024-01-01T00:00:00+00:00",
        )
        assert pipeline.process_item(stale, spider) is stale


class TestBytezPipeline:
    def test_drops_duplicate_urls(self):
        pipeline = BytezPipeline()
        item = BytezItem(
            title="First",
            url="https://Example.com/story/",
            scope="India",
            source="Example",
            language="en",
            scraped_at="2024-01-01T00:00:00+00:00",
        )
        pipeline.process_item(item)

        duplicate = BytezItem(
            title="Duplicate",
            url="https://example.com/story",
            scope="India",
            source="Example",
            language="en",
            scraped_at="2024-01-01T00:00:00+00:00",
        )
        with pytest.raises(DropItem):
            pipeline.process_item(duplicate)

    def test_preserves_body_paragraph_breaks(self):
        pipeline = BytezPipeline()
        item = BytezItem(
            title="Story",
            url="https://example.com/unique-story",
            body="First paragraph.\n\nSecond paragraph.",
            scope="India",
            source="Example",
            language="en",
            scraped_at="2024-01-01T00:00:00+00:00",
        )
        processed = pipeline.process_item(item)
        assert processed["body"] == "First paragraph.\nSecond paragraph."
