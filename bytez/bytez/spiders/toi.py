from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, ClassVar
from urllib.parse import urlparse

import scrapy

from bytez.items import BytezItem
from bytez.spiders.common import (
    ScopeTracker,
    SpiderLimits,
    bounded_links,
    format_published_at,
    parse_spider_limits,
    scope_errback,
    utc_now_iso,
)


class ToiSpider(scrapy.Spider):
    name: ClassVar[str] = "toi"

    allowed_domains: ClassVar[tuple[str, ...]] = (
        "global-feed.indiatimes.com",
        "timesofindia.indiatimes.com",
    )

    INDIA_FEED_URL: ClassVar[str] = (
        "https://global-feed.indiatimes.com/wufs/top-news/fetch/latest/articles/toi"
    )
    WORLD_START_URL: ClassVar[str] = "https://timesofindia.indiatimes.com/world"

    INDIA_SCOPE: ClassVar[str] = "India"
    WORLD_SCOPE: ClassVar[str] = "World"
    SCOPES: ClassVar[tuple[str, ...]] = (INDIA_SCOPE, WORLD_SCOPE)

    SOURCE: ClassVar[str] = "The Times of India"
    LANGUAGE: ClassVar[str] = "en"

    PROMO_MARKERS: ClassVar[tuple[str, ...]] = (
        "You Can Also Check:",
        "Stay updated with the latest",
        "Download the TOI App",
    )

    MAX_TOTAL_ARTICLES: ClassVar[int] = 1000
    OLD_ARTICLE_MAX_AGE: ClassVar[timedelta] = timedelta(days=1)
    MAX_OLD_ARTICLE_RATIO: ClassVar[float] = 0.5
    MIN_ARTICLES_BEFORE_RATIO_CHECK: ClassVar[int] = 200
    MAX_LINKS_PER_PAGE: ClassVar[int] = 15

    DEFAULT_LIMITS: ClassVar[SpiderLimits] = SpiderLimits(
        max_total_articles=MAX_TOTAL_ARTICLES,
        old_article_max_age=OLD_ARTICLE_MAX_AGE,
        max_old_article_ratio=MAX_OLD_ARTICLE_RATIO,
        min_articles_before_ratio_check=MIN_ARTICLES_BEFORE_RATIO_CHECK,
    )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.tracker = ScopeTracker(
            spider.limits,
            stats=crawler.stats,
            logger=spider.logger,
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

    async def start(self):
        yield scrapy.Request(
            self.INDIA_FEED_URL,
            callback=self.parse,
            errback=scope_errback(
                self, self.tracker, self.INDIA_SCOPE, self.SCOPES, label="feed"
            ),
            cb_kwargs={"scope": self.INDIA_SCOPE},
        )

        yield scrapy.Request(
            self.WORLD_START_URL,
            callback=self.parse_world,
            errback=scope_errback(
                self, self.tracker, self.WORLD_SCOPE, self.SCOPES, label="listing"
            ),
            cb_kwargs={"scope": self.WORLD_SCOPE},
        )

    @staticmethod
    def clean_body(body: str | None) -> str:
        if not body:
            return ""

        cutoff = len(body)

        for marker in ToiSpider.PROMO_MARKERS:
            index = body.find(marker)
            if index != -1:
                cutoff = min(cutoff, index)

        return body[:cutoff].rstrip()

    @staticmethod
    def _world_allows_url(url: str) -> bool:
        path = urlparse(url).path
        return "india" not in path.lower()

    def _filter_links_for_scope(self, links: set[str], scope: str) -> list[str]:
        filter_fn = self._world_allows_url if scope == self.WORLD_SCOPE else None
        return bounded_links(links, self.MAX_LINKS_PER_PAGE, filter_fn=filter_fn)

    def closed(self, reason: str) -> None:
        for scope in self.SCOPES:
            self.tracker.log_scope_summary(scope, reason)

    def parse(self, response, scope: str = "India"):
        if self.tracker.is_stopped(scope):
            return

        for article in response.json():
            if self.tracker.is_stopped(scope):
                break

            url = article.get("wu")
            if not url or "/articleshow/" not in url:
                continue

            item = BytezItem(
                title=article.get("hl"),
                url=url,
                scope=scope,
                summary=article.get("des"),
                source=self.SOURCE,
                language=self.LANGUAGE,
            )

            yield response.follow(
                url,
                callback=self.parse_article,
                errback=scope_errback(
                    self, self.tracker, scope, self.SCOPES, label="article"
                ),
                cb_kwargs={"item": item},
            )

        if not self.tracker.is_stopped(scope):
            self.logger.info("%s feed discovery complete: feed exhausted", scope)
            if self.tracker.stats is not None:
                self.tracker.stats.set_value(
                    f"scope/{scope}/discovery_complete",
                    "feed exhausted",
                )

    def parse_world(self, response, scope: str = "World"):
        if self.tracker.is_stopped(scope):
            return

        links = self._filter_links_for_scope(
            self.extract_article_links(response), scope
        )

        if not links:
            self.tracker.handle_scope_stop(scope, "listing exhausted", self.SCOPES)
            return

        for link in links:
            yield response.follow(
                link,
                callback=self.parse_article,
                errback=scope_errback(
                    self, self.tracker, scope, self.SCOPES, label="article"
                ),
                cb_kwargs={"scope": scope},
            )

    def extract_article_links(self, response) -> set[str]:
        links: set[str] = set()

        for href in response.css("a::attr(href)").getall():
            if not href or "/articleshow/" not in href:
                continue

            if not (href.startswith("/") or href.lower().startswith("http")):
                continue

            links.add(response.urljoin(href))

        return links

    @staticmethod
    def _extract_json_ld_article(response) -> dict | None:
        for script in response.xpath(
            '//script[@type="application/ld+json"]/text()'
        ).getall():
            try:
                obj = json.loads(script)
            except json.JSONDecodeError:
                continue

            if isinstance(obj, list):
                obj = next(
                    (
                        entry
                        for entry in obj
                        if isinstance(entry, dict)
                        and (
                            (
                                isinstance(entry.get("@type"), str)
                                and entry["@type"].endswith("Article")
                            )
                            or (
                                isinstance(entry.get("@type"), list)
                                and any(
                                    str(t).endswith("Article") for t in entry["@type"]
                                )
                            )
                        )
                    ),
                    None,
                )

            if isinstance(obj, dict):
                article_type = obj.get("@type", "")

                if isinstance(article_type, list):
                    is_article = any(str(t).endswith("Article") for t in article_type)
                else:
                    is_article = str(article_type).endswith("Article")

                if is_article:
                    return obj

        return None

    @classmethod
    def _populate_from_jsonld(
        cls,
        item: BytezItem,
        data: dict,
        *,
        scope: str,
        response_url: str,
    ) -> BytezItem:
        keywords = data.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [tag.strip() for tag in keywords.split(",") if tag.strip()]
        elif not isinstance(keywords, list):
            keywords = []

        image = data.get("image")
        if isinstance(image, dict):
            image = image.get("url")
        elif isinstance(image, list):
            if image:
                first = image[0]
                image = first.get("url") if isinstance(first, dict) else first
            else:
                image = None

        author = data.get("author")
        if isinstance(author, dict):
            author = author.get("name")
        elif isinstance(author, list):
            author = ", ".join(
                a["name"] for a in author if isinstance(a, dict) and "name" in a
            )

        if not item.title:
            item.title = data.get("headline")
        if not item.url:
            item.url = response_url
        item.scope = scope
        if not item.summary:
            item.summary = data.get("description")
        item.author = author
        item.image = image
        item.published_at = format_published_at(data.get("datePublished"))
        item.body = cls.clean_body(data.get("articleBody"))
        item.tags = keywords
        item.source = cls.SOURCE
        item.language = cls.LANGUAGE
        item.scraped_at = utc_now_iso()
        return item

    def parse_article(
        self,
        response,
        item: BytezItem | None = None,
        scope: str = "India",
    ):
        effective_scope = item.scope if item is not None else scope

        if self.tracker.is_stopped(effective_scope):
            return

        data = self._extract_json_ld_article(response)

        if data is None:
            self.logger.warning("Article JSON-LD not found: %s", response.url)
            links = self._filter_links_for_scope(
                self.extract_article_links(response), effective_scope
            )

            for link in links:
                if link != response.url:
                    yield response.follow(
                        link,
                        callback=self.parse_article,
                        errback=scope_errback(
                            self,
                            self.tracker,
                            effective_scope,
                            self.SCOPES,
                            label="article",
                        ),
                        cb_kwargs={"scope": effective_scope},
                    )
            return

        if item is None:
            item = BytezItem(
                title=data.get("headline"),
                url=response.url,
                scope=effective_scope,
                summary=data.get("description"),
                source=self.SOURCE,
                language=self.LANGUAGE,
            )

        item = self._populate_from_jsonld(
            item,
            data,
            scope=effective_scope,
            response_url=response.url,
        )

        self.tracker.register(item.scope, item.published_at)
        yield item

        stop_reason = self.tracker.should_stop(item.scope)
        if stop_reason is not None:
            self.tracker.handle_scope_stop(item.scope, stop_reason, self.SCOPES)
            return

        links = self._filter_links_for_scope(
            self.extract_article_links(response), item.scope
        )

        for link in links:
            if link == response.url:
                continue

            yield response.follow(
                link,
                callback=self.parse_article,
                errback=scope_errback(
                    self,
                    self.tracker,
                    item.scope,
                    self.SCOPES,
                    label="article",
                ),
                cb_kwargs={"scope": item.scope},
            )
