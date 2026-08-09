from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from bytez.items import BytezItem
from bytez.spiders.hindu import HinduSpider
from tests.conftest import load_fixture


def make_spider(**kwargs) -> HinduSpider:
    crawler = MagicMock()
    crawler.stats = MagicMock()
    return HinduSpider.from_crawler(crawler, **kwargs)


class TestHinduSpider:
    def test_starts_all_scopes(self):
        spider = make_spider()

        async def collect():
            return [request.cb_kwargs["scope"] async for request in spider.start()]

        import asyncio

        scopes = asyncio.run(collect())
        assert scopes == ["Tamil Nadu", "India", "World"]

    def test_listing_item_uses_crawl_scope(self, make_html_response):
        spider = make_spider()
        response = make_html_response(
            HinduSpider.SCOPE_START_URLS["India"],
            load_fixture("hindu", "listing.html"),
        )
        article = response.css("div.element")[0]
        item = spider._listing_item(article, response, "India")
        assert item is not None
        assert item.scope == "India"
        assert item.title == "Listing title"
        assert item.language == "en"

    def test_extract_body_includes_nested_inline_markup(self, make_html_response):
        response = make_html_response(
            "https://www.thehindu.com/news/national/article.ece",
            load_fixture("hindu", "article.html"),
        )
        body = HinduSpider._extract_body(response)
        assert "Opening paragraph with nested emphasis and a link." in body
        assert "Second paragraph." in body

    def test_populate_article_normalizes_fields(self, make_html_response):
        response = make_html_response(
            "https://www.thehindu.com/news/national/article.ece",
            load_fixture("hindu", "article.html"),
        )
        item = BytezItem(
            title="Listing title",
            url=response.url,
            scope="India",
            source="The Hindu",
            language="en",
        )
        item = HinduSpider._populate_article(item, response)
        assert item.summary == "Article summary"
        assert item.published_at == "2024-02-15T08:30:00+05:30"
        assert item.tags == ["Tamil Nadu", "Politics"]
        assert item.author == "Page Author"
        assert item.scraped_at.endswith("+05:30")

    def test_listing_schedules_article_and_pagination(
        self, make_html_response
    ):
        spider = make_spider(
            max_total_articles="10",
            min_articles_before_ratio_check="0",
        )
        response = make_html_response(
            HinduSpider.SCOPE_START_URLS["India"],
            load_fixture("hindu", "listing.html"),
        )
        results = list(spider.parse(response, scope="India"))
        assert len(results) == 2
        assert results[0].url.endswith("sample-article12345678.ece")
        assert "page=2" in results[1].url

    def test_parse_article_registers_and_can_stop_scope(
        self, make_html_response
    ):
        spider = make_spider(
            max_total_articles="1",
            min_articles_before_ratio_check="0",
            max_published_age_hours="0",
        )
        response = make_html_response(
            "https://www.thehindu.com/news/national/article.ece",
            load_fixture("hindu", "article.html"),
        )
        item = BytezItem(
            title="Listing title",
            url=response.url,
            scope="India",
            source="The Hindu",
            language="en",
        )
        results = list(spider.parse_article(response, item=item, scope="India"))
        assert len(results) == 1
        assert spider.tracker.is_stopped("India")

    def test_listing_skips_when_scope_stopped(self, make_html_response):
        spider = make_spider(min_articles_before_ratio_check="0")
        spider.tracker.stop("India", "already stopped")
        response = make_html_response(
            HinduSpider.SCOPE_START_URLS["India"],
            load_fixture("hindu", "listing.html"),
        )
        assert list(spider.parse(response, scope="India")) == []

    def test_runtime_args_override_defaults(self):
        spider = make_spider(
            max_total_articles="40",
            old_article_max_age_days="1",
            max_old_article_ratio="0.4",
            min_articles_before_ratio_check="5",
        )
        assert spider.limits.max_total_articles == 40
        assert spider.limits.old_article_max_age == timedelta(days=1)

    def test_listing_marks_discovery_complete_when_articles_scheduled(
        self, make_html_response
    ):
        spider = make_spider(min_articles_before_ratio_check="0")
        html = load_fixture("hindu", "listing.html").replace(
            '<li class="page-item next"><a href="/news/national/?page=2">Next</a></li>',
            "",
        )
        response = make_html_response(
            HinduSpider.SCOPE_START_URLS["India"],
            html,
        )
        list(spider.parse(response, scope="India"))
        assert not spider.tracker.is_stopped("India")
        spider.tracker.stats.set_value.assert_any_call(
            "scope/India/discovery_complete",
            "listing exhausted",
        )

    def test_listing_exhausted_stops_empty_scope(self, make_html_response):
        spider = make_spider(min_articles_before_ratio_check="0")
        response = make_html_response(
            HinduSpider.SCOPE_START_URLS["India"],
            "<html><body><p>No articles</p></body></html>",
        )
        list(spider.parse(response, scope="India"))
        assert spider.tracker.stopped_scopes["India"] == "listing exhausted"
