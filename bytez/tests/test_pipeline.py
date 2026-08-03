from __future__ import annotations

import pytest
from scrapy.exceptions import DropItem

from bytez.items import BytezItem
from bytez.pipelines import BytezPipeline


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
