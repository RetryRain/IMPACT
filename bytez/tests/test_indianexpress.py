from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

from bytez.spiders.indianexpress import IndianExpressSpider
from tests.conftest import load_json_fixture


def make_spider(**kwargs) -> IndianExpressSpider:
    crawler = MagicMock()
    crawler.stats = MagicMock()
    return IndianExpressSpider.from_crawler(crawler, **kwargs)


class TestIndianExpressSpider:
    def test_builds_item_and_excludes_promotional_content(self):
        story = load_json_fixture("indianexpress", "api_page.json")["items"][0]["story"]
        item = IndianExpressSpider._item_from_story(story, "India")

        assert item is not None
        assert item.title == "Sample headline"
        assert item.scope == "India"
        assert item.language == "en"
        assert item.source == "The New Indian Express"
        assert item.tags == ["Politics"]
        assert item.image == "https://images.example.com/hero.jpg"
        assert item.published_at == "2024-01-01T00:00:00+00:00"
        assert "First paragraph with bold text." in item.body
        assert "Also read" not in item.body
        assert "Promo block" not in item.body
        assert "Linked story teaser" not in item.body
        assert "Second paragraph." in item.body
        assert item.scraped_at.endswith("+00:00")

    def test_uses_cdn_fallback_when_original_image_url_is_missing(self):
        story = {
            "url": "https://www.newindianexpress.com/story.html",
            "headline": "Headline",
            "hero-image-s3-key": "/media/photo.jpg",
            "cards": [],
        }
        item = IndianExpressSpider._item_from_story(story, "India")
        assert item.image == (
            "https://d3lzcn6mbbadaf.cloudfront.net/media/photo.jpg"
        )

    def test_builds_expected_paginated_request(self):
        spider = make_spider()
        request = spider._api_request(
            "India",
            "https://www.newindianexpress.com/api/v1/collections/india",
            offset=8,
        )
        assert "offset=8" in request.url
        assert "limit=8" in request.url
        assert request.cb_kwargs["scope"] == "India"

    def test_starts_all_collections(self):
        spider = make_spider()

        async def collect():
            return [request.cb_kwargs["scope"] async for request in spider.start()]

        import asyncio

        scopes = asyncio.run(collect())
        assert scopes == ["India", "Tamil Nadu", "World"]

    def test_excludes_linked_story_metadata_variants(self):
        assert IndianExpressSpider._is_linked_story({"linked-story-id": "x"})
        assert IndianExpressSpider._is_linked_story(
            {"linked-story": {"id": "x"}}
        )
        assert not IndianExpressSpider._is_linked_story({})
        assert not IndianExpressSpider._is_linked_story(None)

    def test_empty_api_response_stops_scope(self, make_json_response):
        spider = make_spider(max_total_articles=10, min_articles_before_ratio_check=0)
        payload = load_json_fixture("indianexpress", "empty_api_page.json")
        response = make_json_response(
            "https://www.newindianexpress.com/api/v1/collections/india",
            payload,
        )
        list(
            spider.parse(
                response,
                scope="India",
                api_url="https://www.newindianexpress.com/api/v1/collections/india",
                offset=0,
            )
        )
        assert spider.tracker.is_stopped("India")
        assert spider.tracker.stopped_scopes["India"] == "API returned no items"

    def test_runtime_args_override_defaults(self):
        spider = make_spider(
            max_total_articles="50",
            old_article_max_age_days="1",
            max_old_article_ratio="0.25",
            min_articles_before_ratio_check="10",
        )
        assert spider.limits.max_total_articles == 50
        assert spider.limits.old_article_max_age == timedelta(days=1)
        assert spider.limits.max_old_article_ratio == 0.25
        assert spider.limits.min_articles_before_ratio_check == 10

    def test_article_cap_behavior(self, make_json_response):
        spider = make_spider(
            max_total_articles="1",
            min_articles_before_ratio_check="0",
        )
        payload = load_json_fixture("indianexpress", "api_page.json")
        response = make_json_response(
            "https://www.newindianexpress.com/api/v1/collections/india",
            payload,
        )
        items = list(
            spider.parse(
                response,
                scope="India",
                api_url="https://www.newindianexpress.com/api/v1/collections/india",
                offset=0,
            )
        )
        scraped = [value for value in items if hasattr(value, "url")]
        assert len(scraped) == 1
        assert spider.tracker.is_stopped("India")
