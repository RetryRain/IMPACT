from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from scrapy.exceptions import CloseSpider

from bytez.items import BytezItem
from bytez.spiders.toi import ToiSpider
from tests.conftest import load_fixture, load_json_fixture


def make_spider(**kwargs) -> ToiSpider:
    crawler = MagicMock()
    crawler.stats = MagicMock()
    crawler.bytez_stopped_scope_keys = set()
    return ToiSpider.from_crawler(crawler, **kwargs)


class TestToiSpider:
    def test_clean_body_trims_promotional_tail(self):
        body = "Lead paragraph. You Can Also Check: more links"
        assert ToiSpider.clean_body(body) == "Lead paragraph."

    def test_filter_links_for_world_is_deterministic(self):
        spider = make_spider()
        links = {
            "https://timesofindia.indiatimes.com/world/us/articleshow/2.cms",
            "https://timesofindia.indiatimes.com/world/uk/articleshow/1.cms",
            "https://timesofindia.indiatimes.com/india/sample/articleshow/3.cms",
        }
        filtered = spider._filter_links_for_scope(links, ToiSpider.WORLD_SCOPE)
        assert filtered == [
            "https://timesofindia.indiatimes.com/world/uk/articleshow/1.cms",
            "https://timesofindia.indiatimes.com/world/us/articleshow/2.cms",
        ]

    def test_india_feed_schedules_only_articleshow_links(self, make_json_response):
        spider = make_spider(min_articles_before_ratio_check="0")
        payload = load_json_fixture("toi", "india_feed.json")
        response = make_json_response(ToiSpider.INDIA_FEED_URL, payload)
        results = list(spider.parse(response, scope=ToiSpider.INDIA_SCOPE))
        assert len(results) == 1
        assert "/articleshow/" in results[0].url

    def test_india_feed_marks_discovery_complete_without_stopping_scope(
        self, make_json_response
    ):
        spider = make_spider(min_articles_before_ratio_check="0")
        payload = load_json_fixture("toi", "india_feed.json")
        response = make_json_response(ToiSpider.INDIA_FEED_URL, payload)
        list(spider.parse(response, scope=ToiSpider.INDIA_SCOPE))
        assert not spider.tracker.is_stopped(ToiSpider.INDIA_SCOPE)
        spider.tracker.stats.set_value.assert_any_call(
            f"scope/{ToiSpider.INDIA_SCOPE}/discovery_complete",
            "feed exhausted",
        )

    def test_india_feed_skips_when_scope_stopped(self, make_json_response):
        spider = make_spider(min_articles_before_ratio_check="0")
        spider.tracker.stop(ToiSpider.INDIA_SCOPE, "already stopped")
        payload = load_json_fixture("toi", "india_feed.json")
        response = make_json_response(ToiSpider.INDIA_FEED_URL, payload)
        assert list(spider.parse(response, scope=ToiSpider.INDIA_SCOPE)) == []

    def test_populate_from_jsonld_normalizes_timestamps(self, make_html_response):
        spider = make_spider()
        response = make_html_response(
            "https://timesofindia.indiatimes.com/world/sample/articleshow/1.cms",
            load_fixture("toi", "article.html"),
        )
        data = spider._extract_json_ld_article(response)
        item = BytezItem(url=response.url, scope="World")
        item = spider._populate_from_jsonld(
            item, data, scope="World", response_url=response.url
        )
        assert item.published_at == "2024-01-01T12:00:00+00:00"
        assert item.scraped_at.endswith("+00:00")
        assert item.language == "en"
        assert item.body == "Body paragraph one."

    def test_parse_article_registers_item_and_expands_links_for_world(
        self, make_html_response
    ):
        spider = make_spider(
            max_total_articles="10",
            min_articles_before_ratio_check="0",
        )
        response = make_html_response(
            "https://timesofindia.indiatimes.com/world/sample/articleshow/1.cms",
            load_fixture("toi", "article.html"),
        )
        results = list(spider.parse_article(response, scope="World"))
        item = results[0]
        assert item.title == "JSON-LD headline"
        assert item.source == "The Times of India"
        follow_ups = [value for value in results[1:] if hasattr(value, "callback")]
        assert follow_ups
        assert spider.tracker.total_articles["World"] == 1

    def test_parse_article_does_not_expand_links_for_india(
        self, make_html_response
    ):
        spider = make_spider(
            max_total_articles="10",
            min_articles_before_ratio_check="0",
        )
        response = make_html_response(
            "https://timesofindia.indiatimes.com/india/sample/articleshow/1.cms",
            load_fixture("toi", "article.html"),
        )
        results = list(spider.parse_article(response, scope=ToiSpider.INDIA_SCOPE))
        assert len(results) == 1
        assert results[0].title == "JSON-LD headline"

    def test_stopped_scope_registers_in_crawler_sink(self):
        spider = make_spider(min_articles_before_ratio_check="0")
        spider.tracker.stop(ToiSpider.INDIA_SCOPE, "test stop")
        assert "toi/India" in spider.crawler.bytez_stopped_scope_keys

    def test_runtime_args_override_defaults(self):
        spider = make_spider(
            max_total_articles="25",
            old_article_max_age_days="2",
            max_old_article_ratio="0.25",
            min_articles_before_ratio_check="5",
        )
        assert spider.limits.max_total_articles == 25
        assert spider.limits.old_article_max_age == timedelta(days=2)

    def test_empty_world_listing_stops_scope(self, make_html_response):
        spider = make_spider(min_articles_before_ratio_check="0")
        response = make_html_response(
            ToiSpider.WORLD_START_URL,
            "<html><body><p>No links</p></body></html>",
        )
        list(spider.parse_world(response, scope=ToiSpider.WORLD_SCOPE))
        assert (
            spider.tracker.stopped_scopes[ToiSpider.WORLD_SCOPE]
            == "listing exhausted"
        )

    def test_close_spider_when_all_scopes_stop(self):
        spider = make_spider(min_articles_before_ratio_check="0")
        spider.tracker.stop("India", "reached max_total_articles=5")
        with pytest.raises(CloseSpider):
            spider.tracker.handle_scope_stop(
                "World", "listing exhausted", ToiSpider.SCOPES
            )
