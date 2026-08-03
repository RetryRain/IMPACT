from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar
from urllib.parse import urlencode

import scrapy
from scrapy.selector import Selector

from bytez.items import BytezItem
from bytez.spiders.common import (
    ScopeTracker,
    SpiderLimits,
    parse_spider_limits,
    scope_errback,
    utc_now_iso,
)


class IndianExpressSpider(scrapy.Spider):
    """Collect India and Tamil Nadu stories from The New Indian Express API."""

    name: ClassVar[str] = "indianexpress"
    allowed_domains: ClassVar[tuple[str, ...]] = ("newindianexpress.com",)

    INDIA_SCOPE: ClassVar[str] = "India"
    TAMIL_NADU_SCOPE: ClassVar[str] = "Tamil Nadu"
    WORLD_SCOPE: ClassVar[str] = "World"
    COLLECTION_URLS: ClassVar[dict[str, str]] = {
        INDIA_SCOPE: "https://www.newindianexpress.com/api/v1/collections/india",
        TAMIL_NADU_SCOPE: (
            "https://www.newindianexpress.com/api/v1/collections/tamil-nadu-states"
        ),
        WORLD_SCOPE: "https://www.newindianexpress.com/api/v1/collections/world",
    }
    SCOPES: ClassVar[tuple[str, ...]] = (
        INDIA_SCOPE,
        TAMIL_NADU_SCOPE,
        WORLD_SCOPE,
    )

    PAGE_SIZE: ClassVar[int] = 8
    SOURCE: ClassVar[str] = "The New Indian Express"
    LANGUAGE: ClassVar[str] = "en"
    IMAGE_CDN_URL: ClassVar[str] = "https://d3lzcn6mbbadaf.cloudfront.net/"
    BROWSER_USER_AGENT: ClassVar[str] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )
    custom_settings: ClassVar[dict[str, str]] = {"USER_AGENT": BROWSER_USER_AGENT}

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

    async def start(self) -> AsyncIterator[scrapy.Request]:
        for scope, api_url in self.COLLECTION_URLS.items():
            yield self._api_request(scope, api_url, offset=0)

    def _api_request(self, scope: str, api_url: str, offset: int) -> scrapy.Request:
        query = urlencode(
            {"item-type": "story", "offset": offset, "limit": self.PAGE_SIZE}
        )
        return scrapy.Request(
            f"{api_url}?{query}",
            callback=self.parse,
            errback=scope_errback(self, self.tracker, scope, self.SCOPES),
            cb_kwargs={"scope": scope, "api_url": api_url, "offset": offset},
        )

    @staticmethod
    def _published_at(value: object) -> str | None:
        if not isinstance(value, (int, float)):
            return None
        try:
            return (
                datetime.fromtimestamp(value / 1000, tz=UTC)
                .replace(microsecond=0)
                .isoformat()
            )
        except (OverflowError, OSError, ValueError):
            return None

    @staticmethod
    def _is_linked_story(metadata: object) -> bool:
        if not isinstance(metadata, dict):
            return False
        if metadata.get("linked-story-id"):
            return True
        linked_story = metadata.get("linked-story")
        return isinstance(linked_story, dict) and bool(linked_story)

    @staticmethod
    def _extract_body(cards: object) -> str:
        if not isinstance(cards, list):
            return ""

        paragraphs: list[str] = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            elements = card.get("story-elements")
            if not isinstance(elements, list):
                continue

            for element in elements:
                if not isinstance(element, dict) or element.get("type") != "text":
                    continue

                metadata = element.get("metadata")
                if (
                    element.get("subtype") == "also-read"
                    or (
                        isinstance(metadata, dict)
                        and metadata.get("promotional-message")
                    )
                    or IndianExpressSpider._is_linked_story(metadata)
                ):
                    continue

                html = element.get("text")
                if not isinstance(html, str):
                    continue

                for paragraph in Selector(text=html).xpath("//p"):
                    cleaned = " ".join(
                        "".join(paragraph.xpath(".//text()").getall()).split()
                    )
                    if cleaned:
                        paragraphs.append(cleaned)

        return "\n".join(paragraphs)

    @classmethod
    def _image_url(cls, story: dict[str, object]) -> str | None:
        metadata = story.get("hero-image-metadata")
        if isinstance(metadata, dict):
            original_url = metadata.get("original-url")
            if isinstance(original_url, str) and original_url:
                return original_url

        key = story.get("hero-image-s3-key")
        if isinstance(key, str) and key:
            return f"{cls.IMAGE_CDN_URL}{key.lstrip('/')}"
        return None

    @classmethod
    def _item_from_story(
        cls, story: dict[str, object], default_scope: str
    ) -> BytezItem | None:
        url = story.get("url")
        if not isinstance(url, str) or not url:
            return None

        scope = default_scope
        sections = story.get("sections")
        if isinstance(sections, list) and sections and isinstance(sections[0], dict):
            display_name = sections[0].get("display-name")
            if isinstance(display_name, str) and display_name:
                scope = display_name

        tags = story.get("tags")
        tag_names = (
            [
                tag["name"]
                for tag in tags
                if isinstance(tag, dict) and isinstance(tag.get("name"), str)
            ]
            if isinstance(tags, list)
            else []
        )

        return BytezItem(
            title=story.get("headline")
            if isinstance(story.get("headline"), str)
            else None,
            url=url,
            scope=scope,
            author=story.get("author-name")
            if isinstance(story.get("author-name"), str)
            else None,
            summary=story.get("subheadline")
            if isinstance(story.get("subheadline"), str)
            else None,
            image=cls._image_url(story),
            published_at=cls._published_at(story.get("published-at")),
            body=cls._extract_body(story.get("cards")),
            tags=tag_names,
            source=cls.SOURCE,
            language=cls.LANGUAGE,
            scraped_at=utc_now_iso(),
        )

    def parse(
        self,
        response: scrapy.http.Response,
        scope: str,
        api_url: str,
        offset: int,
    ):
        if self.tracker.is_stopped(scope):
            return

        payload = response.json()
        items = payload.get("items", []) if isinstance(payload, dict) else []
        if not isinstance(items, list) or not items:
            self.tracker.handle_scope_stop(scope, "API returned no items", self.SCOPES)
            return

        for entry in items:
            if self.tracker.total_articles.get(scope, 0) >= self.limits.max_total_articles:
                self.tracker.handle_scope_stop(
                    scope,
                    self.tracker.should_stop(scope) or "article limit reached",
                    self.SCOPES,
                )
                break

            story = entry.get("story") if isinstance(entry, dict) else None
            if not isinstance(story, dict):
                self.logger.warning("[%s] skipping API item without a story", scope)
                continue

            item = self._item_from_story(story, scope)
            if item is None:
                self.logger.warning("[%s] skipping story without a URL", scope)
                continue

            self.tracker.register(scope, item.published_at)
            yield item

            stop_reason = self.tracker.should_stop(scope)
            if stop_reason:
                self.tracker.handle_scope_stop(scope, stop_reason, self.SCOPES)
                break

        if not self.tracker.is_stopped(scope):
            yield self._api_request(scope, api_url, offset + self.PAGE_SIZE)

    def closed(self, reason: str) -> None:
        for scope in self.SCOPES:
            self.tracker.log_scope_summary(scope, reason)
