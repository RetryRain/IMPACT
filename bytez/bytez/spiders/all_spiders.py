from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, ClassVar

import scrapy

from bytez.spiders.common import parse_spider_limits
from bytez.spiders.hindu import HinduSpider
from bytez.spiders.indianexpress import IndianExpressSpider
from bytez.spiders.toi import ToiSpider


class AllSpidersSpider(scrapy.Spider):
    """Run hindu, toi, and indianexpress in a single crawl.

    Use with Scrapy feed exports to collect every publisher into one file:

        scrapy crawl all_spiders -O data.json
        scrapy crawl all_spiders -o data.jsonl

    Runtime limits (`-a max_total_articles=...`, etc.) are forwarded to each
    child spider.
    """

    name: ClassVar[str] = "all_spiders"

    CHILD_SPIDER_CLASSES: ClassVar[tuple[type[scrapy.Spider], ...]] = (
        IndianExpressSpider,
        ToiSpider,
        HinduSpider,
    )

    allowed_domains: ClassVar[tuple[str, ...]] = (
        "newindianexpress.com",
        "global-feed.indiatimes.com",
        "timesofindia.indiatimes.com",
        "thehindu.com",
    )

    custom_settings: ClassVar[dict[str, str]] = IndianExpressSpider.custom_settings

    def __init__(
        self,
        *args: Any,
        max_total_articles: str | None = None,
        old_article_max_age_days: str | None = None,
        max_old_article_ratio: str | None = None,
        min_articles_before_ratio_check: str | None = None,
        max_published_age_hours: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.limits = parse_spider_limits(
            max_total_articles=max_total_articles,
            old_article_max_age_days=old_article_max_age_days,
            max_old_article_ratio=max_old_article_ratio,
            min_articles_before_ratio_check=min_articles_before_ratio_check,
            max_published_age_hours=max_published_age_hours,
            defaults=IndianExpressSpider.DEFAULT_LIMITS,
        )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider._children: list[scrapy.Spider] = []
        for spider_cls in cls.CHILD_SPIDER_CLASSES:
            child = spider_cls.from_crawler(crawler, *args, **kwargs)
            if child.tracker is not None:
                child.tracker.close_on_all_scopes = False
            spider._children.append(child)
        return spider

    async def start(self) -> AsyncIterator[scrapy.Request]:
        for child in self._children:
            async for request in child.start():
                yield request

    def closed(self, reason: str) -> None:
        total_articles = 0
        for child in self._children:
            child.closed(reason)
            tracker = getattr(child, "tracker", None)
            if tracker is not None:
                total_articles += sum(tracker.fresh_articles.values())

        self.logger.info(
            "all_spiders crawl finished: reason=%s total_articles=%d",
            reason,
            total_articles,
        )
