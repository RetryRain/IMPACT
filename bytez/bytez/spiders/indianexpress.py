from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar
from urllib.parse import urlencode

import scrapy
from scrapy.selector import Selector

from bytez.items import BytezItem


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
    LANGUAGE: ClassVar[str] = "English"
    IMAGE_CDN_URL: ClassVar[str] = "https://d3lzcn6mbbadaf.cloudfront.net/"
    BROWSER_USER_AGENT: ClassVar[str] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )
    custom_settings: ClassVar[dict[str, str]] = {"USER_AGENT": BROWSER_USER_AGENT}

    # Limits apply independently to each collection, matching the project's
    # multi-scope crawl behavior in the Times of India spider.
    MAX_TOTAL_ARTICLES: ClassVar[int] = 1000
    OLD_ARTICLE_MAX_AGE: ClassVar[timedelta] = timedelta(days=2)
    MAX_OLD_ARTICLE_RATIO: ClassVar[float] = 0.5
    MIN_ARTICLES_BEFORE_RATIO_CHECK: ClassVar[int] = 200

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
        self.max_total_articles = self._positive_int(
            max_total_articles, self.MAX_TOTAL_ARTICLES
        )
        self.old_article_max_age = timedelta(
            days=self._positive_float(
                old_article_max_age_days,
                self.OLD_ARTICLE_MAX_AGE.total_seconds() / 86_400,
            )
        )
        self.max_old_article_ratio = self._ratio(
            max_old_article_ratio, self.MAX_OLD_ARTICLE_RATIO
        )
        self.min_articles_before_ratio_check = self._positive_int(
            min_articles_before_ratio_check,
            self.MIN_ARTICLES_BEFORE_RATIO_CHECK,
            allow_zero=True,
        )
        self.total_articles: dict[str, int] = {}
        self.old_articles: dict[str, int] = {}
        self.stopped_scopes: dict[str, str] = {}

    @staticmethod
    def _positive_int(value: str | None, default: int, allow_zero: bool = False) -> int:
        if value is None:
            return default
        try:
            parsed = int(value)
        except ValueError as error:
            raise ValueError(f"Expected an integer, got {value!r}") from error
        if parsed < 0 or (parsed == 0 and not allow_zero):
            raise ValueError(f"Expected a positive integer, got {value!r}")
        return parsed

    @staticmethod
    def _positive_float(value: str | None, default: float) -> float:
        if value is None:
            return default
        try:
            parsed = float(value)
        except ValueError as error:
            raise ValueError(f"Expected a positive number, got {value!r}") from error
        if parsed <= 0:
            raise ValueError(f"Expected a positive number, got {value!r}")
        return parsed

    @staticmethod
    def _ratio(value: str | None, default: float) -> float:
        if value is None:
            return default
        try:
            parsed = float(value)
        except ValueError as error:
            raise ValueError(f"Expected a ratio, got {value!r}") from error
        if not 0 <= parsed <= 1:
            raise ValueError(f"Expected a ratio from 0 to 1, got {value!r}")
        return parsed

    def start_requests(self):
        for scope, api_url in self.COLLECTION_URLS.items():
            yield self._api_request(scope, api_url, offset=0)

    async def start(self) -> AsyncIterator[scrapy.Request]:
        for request in self.start_requests():
            yield request

    def _api_request(self, scope: str, api_url: str, offset: int) -> scrapy.Request:
        query = urlencode(
            {"item-type": "story", "offset": offset, "limit": self.PAGE_SIZE}
        )
        return scrapy.Request(
            f"{api_url}?{query}",
            callback=self.parse,
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
    def _parse_published_at(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _is_old(self, published_at: str | None) -> bool:
        parsed = self._parse_published_at(published_at)
        return (
            parsed is not None
            and (datetime.now(UTC) - parsed) > self.old_article_max_age
        )

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
                is_linked_story = isinstance(metadata, dict) and bool(
                    metadata.get("linked-story-id")
                )
                if (
                    element.get("subtype") == "also-read"
                    or (
                        isinstance(metadata, dict)
                        and metadata.get("promotional-message")
                    )
                    or is_linked_story
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
            scraped_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        )

    def _register_article(self, scope: str, published_at: str | None) -> None:
        self.total_articles[scope] = self.total_articles.get(scope, 0) + 1
        if self._is_old(published_at):
            self.old_articles[scope] = self.old_articles.get(scope, 0) + 1

    def _should_stop(self, scope: str) -> str | None:
        total = self.total_articles.get(scope, 0)
        if total >= self.max_total_articles:
            return f"reached max_total_articles={self.max_total_articles}"
        if total >= self.min_articles_before_ratio_check:
            old = self.old_articles.get(scope, 0)
            ratio = old / total
            if ratio > self.max_old_article_ratio:
                return (
                    f"old-article ratio {ratio:.2%} exceeded "
                    f"max_old_article_ratio={self.max_old_article_ratio:.2%} "
                    f"(old={old}, total={total})"
                )
        return None

    def _stop_scope(self, scope: str, reason: str) -> None:
        if scope not in self.stopped_scopes:
            self.stopped_scopes[scope] = reason
            self.logger.info("%s crawl finished: %s", scope, reason)

    def parse(
        self,
        response: scrapy.http.Response,
        scope: str,
        api_url: str,
        offset: int,
    ):
        if scope in self.stopped_scopes:
            return

        payload = response.json()
        items = payload.get("items", []) if isinstance(payload, dict) else []
        if not isinstance(items, list) or not items:
            self._stop_scope(scope, "API returned no items")
            return

        for entry in items:
            if self.total_articles.get(scope, 0) >= self.max_total_articles:
                self._stop_scope(
                    scope, self._should_stop(scope) or "article limit reached"
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

            self._register_article(scope, item.published_at)
            yield item

            stop_reason = self._should_stop(scope)
            if stop_reason:
                self._stop_scope(scope, stop_reason)
                break

        if scope not in self.stopped_scopes:
            yield self._api_request(scope, api_url, offset + self.PAGE_SIZE)

    def closed(self, reason: str) -> None:
        for scope in self.SCOPES:
            total = self.total_articles.get(scope, 0)
            old = self.old_articles.get(scope, 0)
            ratio = old / total if total else 0.0
            self.logger.info(
                "[%s] articles=%d old=%d old_ratio=%.2f%% stop_reason=%s",
                scope,
                total,
                old,
                ratio * 100,
                self.stopped_scopes.get(scope, reason),
            )
