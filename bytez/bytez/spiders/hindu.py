from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any, ClassVar

import scrapy

from bytez.items import BytezItem
from bytez.spiders.common import (
    ScopeTracker,
    SpiderLimits,
    format_published_at,
    make_scope_meta,
    parse_spider_limits,
    scope_errback,
    utc_now_iso,
)


class HinduSpider(scrapy.Spider):
    name: ClassVar[str] = "hindu"
    allowed_domains: ClassVar[tuple[str, ...]] = ("thehindu.com",)

    TAMIL_NADU_SCOPE: ClassVar[str] = "Tamil Nadu"
    INDIA_SCOPE: ClassVar[str] = "India"
    WORLD_SCOPE: ClassVar[str] = "World"

    SCOPE_START_URLS: ClassVar[dict[str, str]] = {
        TAMIL_NADU_SCOPE: "https://www.thehindu.com/news/national/tamil-nadu/",
        INDIA_SCOPE: "https://www.thehindu.com/news/national/",
        WORLD_SCOPE: "https://www.thehindu.com/news/international/",
    }
    SCOPES: ClassVar[tuple[str, ...]] = tuple(SCOPE_START_URLS.keys())

    SOURCE: ClassVar[str] = "The Hindu"
    LANGUAGE: ClassVar[str] = "en"

    MAX_TOTAL_ARTICLES: ClassVar[int] = 1000
    OLD_ARTICLE_MAX_AGE: ClassVar[timedelta] = timedelta(days=2)
    MAX_OLD_ARTICLE_RATIO: ClassVar[float] = 0.5
    MIN_ARTICLES_BEFORE_RATIO_CHECK: ClassVar[int] = 200

    DEFAULT_LIMITS: ClassVar[SpiderLimits] = SpiderLimits(
        max_total_articles=MAX_TOTAL_ARTICLES,
        old_article_max_age=OLD_ARTICLE_MAX_AGE,
        max_old_article_ratio=MAX_OLD_ARTICLE_RATIO,
        min_articles_before_ratio_check=MIN_ARTICLES_BEFORE_RATIO_CHECK,
    )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        if not hasattr(crawler, "bytez_stopped_scope_keys"):
            crawler.bytez_stopped_scope_keys = set()
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.tracker = ScopeTracker(
            spider.limits,
            stats=crawler.stats,
            logger=spider.logger,
            scope_prefix=cls.name,
            stopped_scope_sink=crawler.bytez_stopped_scope_keys,
        )
        return spider

    def __init__(
        self,
        *args: Any,
        max_total_articles: str | None = None,
        old_article_max_age_days: str | None = None,
        max_old_article_ratio: str | None = None,
        min_articles_before_ratio_check: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.limits = parse_spider_limits(
            max_total_articles=max_total_articles,
            old_article_max_age_days=old_article_max_age_days,
            max_old_article_ratio=max_old_article_ratio,
            min_articles_before_ratio_check=min_articles_before_ratio_check,
            defaults=self.DEFAULT_LIMITS,
        )
        self.tracker: ScopeTracker | None = None

    async def start(self) -> AsyncIterator[scrapy.Request]:
        for scope, url in self.SCOPE_START_URLS.items():
            yield scrapy.Request(
                url,
                callback=self.parse,
                errback=scope_errback(
                    self, self.tracker, scope, self.SCOPES, label="listing"
                ),
                meta=make_scope_meta(self.name, scope),
                cb_kwargs={"scope": scope},
            )

    @classmethod
    def _listing_item(
        cls, article, response, scope: str
    ) -> BytezItem | None:
        url = article.css("h3.title a::attr(href)").get()
        if not url or "/news/" not in url:
            return None

        url = response.urljoin(url)

        title = " ".join(
            t.strip()
            for t in article.css("h3.title a ::text").getall()
            if t.strip()
        )

        author = article.css(".author-name a::text").get(default="").strip()
        summary = article.css(".sub-text a::text").get(default="").strip()

        image = (
            article.css(".picture img::attr(data-original)").get()
            or article.css(".picture img::attr(data-src-template)").get()
            or article.css(".picture img::attr(src)").get()
        )

        return BytezItem(
            title=title,
            url=url,
            scope=scope,
            author=author,
            summary=summary,
            image=image,
            source=cls.SOURCE,
            language=cls.LANGUAGE,
        )

    @classmethod
    def _extract_body(cls, response) -> str:
        paragraphs: list[str] = []
        for paragraph in response.css(
            "div.articlebodycontent div.schemaDiv[itemprop='articleBody'] p"
        ):
            cleaned = " ".join(
                "".join(paragraph.xpath(".//text()").getall()).split()
            )
            if cleaned:
                paragraphs.append(cleaned)
        return "\n".join(paragraphs)

    @classmethod
    def _populate_article(cls, item: BytezItem, response) -> BytezItem:
        item.body = cls._extract_body(response)

        item.summary = (
            response.css('meta[itemprop="description"]::attr(content)')
            .get(default="")
            .strip()
            or item.summary
        )

        published_at = response.css(
            'meta[itemprop="datePublished"]::attr(content)'
        ).get()
        item.published_at = format_published_at(published_at)

        raw_keywords = response.css('meta[itemprop="keywords"]::attr(content)').get(
            default=""
        )
        item.tags = [tag.strip() for tag in raw_keywords.split(",") if tag.strip()]

        if not item.author:
            item.author = (
                response.css(".author-name a::text").get(default="").strip()
                or response.css(
                    'span[itemprop="author"] meta[itemprop="name"]::attr(content)'
                )
                .get(default="")
                .strip()
            )

        item.source = cls.SOURCE
        item.language = cls.LANGUAGE
        item.scraped_at = utc_now_iso()
        return item

    def parse(self, response, scope: str):
        if self.tracker.is_stopped(scope):
            return

        scheduled = False
        for article in response.css("div.element"):
            if self.tracker.is_stopped(scope):
                break

            if self.tracker.total_articles.get(scope, 0) >= self.limits.max_total_articles:
                self.tracker.handle_scope_stop(
                    scope,
                    self.tracker.should_stop(scope) or "article limit reached",
                    self.SCOPES,
                )
                break

            item = self._listing_item(article, response, scope)
            if item is None:
                continue

            label = article.css(".label a::text").get(default="").strip()
            if label and label != scope:
                self.logger.debug(
                    "[%s] listing label %r differs from crawl scope", scope, label
                )

            yield response.follow(
                item.url,
                callback=self.parse_article,
                errback=scope_errback(
                    self, self.tracker, scope, self.SCOPES, label="article"
                ),
                meta=make_scope_meta(self.name, scope),
                cb_kwargs={"item": item, "scope": scope},
            )
            scheduled = True

        if self.tracker.is_stopped(scope):
            return

        next_page = response.css(
            "li.page-item.next:not(.disabled) a::attr(href)"
        ).get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse,
                errback=scope_errback(
                    self, self.tracker, scope, self.SCOPES, label="listing"
                ),
                meta=make_scope_meta(self.name, scope),
                cb_kwargs={"scope": scope},
            )
        elif not scheduled:
            self.tracker.handle_scope_stop(scope, "listing exhausted", self.SCOPES)
        else:
            self.logger.info(
                "%s listing discovery complete: listing exhausted", scope
            )
            if self.tracker.stats is not None:
                self.tracker.stats.set_value(
                    f"scope/{scope}/discovery_complete",
                    "listing exhausted",
                )

    def parse_article(self, response, item: BytezItem, scope: str):
        if self.tracker.is_stopped(scope):
            return

        item = self._populate_article(item, response)

        self.tracker.register(scope, item.published_at)
        yield item

        stop_reason = self.tracker.should_stop(scope)
        if stop_reason:
            self.tracker.handle_scope_stop(scope, stop_reason, self.SCOPES)

    def closed(self, reason: str) -> None:
        for scope in self.SCOPES:
            self.tracker.log_scope_summary(scope, reason)
