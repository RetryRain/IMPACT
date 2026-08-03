from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar
from urllib.parse import urlencode

import scrapy
from scrapy.selector import Selector

from bytez.items import BytezItem


class TnieSpider(scrapy.Spider):
    """Collect Tamil Nadu stories directly from The New Indian Express API."""

    name: ClassVar[str] = "tnie"
    allowed_domains: ClassVar[tuple[str, ...]] = ("newindianexpress.com",)

    API_URL: ClassVar[str] = (
        "https://www.newindianexpress.com/api/v1/collections/tamil-nadu-states"
    )
    PAGE_SIZE: ClassVar[int] = 8
    SCOPE: ClassVar[str] = "Tamil Nadu"
    SOURCE: ClassVar[str] = "The New Indian Express"
    LANGUAGE: ClassVar[str] = "English"
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
        self.total_articles = 0
        self.old_articles = 0
        self.stop_reason: str | None = None

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
        yield self._api_request(offset=0)

    async def start(self) -> AsyncIterator[scrapy.Request]:
        """Use Scrapy's current startup hook while retaining start_requests()."""
        for request in self.start_requests():
            yield request

    def _api_request(self, offset: int) -> scrapy.Request:
        query = urlencode(
            {"item-type": "story", "offset": offset, "limit": self.PAGE_SIZE}
        )
        return scrapy.Request(
            f"{self.API_URL}?{query}",
            callback=self.parse,
            cb_kwargs={"offset": offset},
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
                if isinstance(metadata, dict) and metadata.get("promotional-message"):
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
    def _item_from_story(cls, story: dict[str, object]) -> BytezItem | None:
        url = story.get("url")
        if not isinstance(url, str) or not url:
            return None

        sections = story.get("sections")
        scope = cls.SCOPE
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
            author=(
                story.get("author-name")
                if isinstance(story.get("author-name"), str)
                else None
            ),
            summary=(
                story.get("subheadline")
                if isinstance(story.get("subheadline"), str)
                else None
            ),
            image=cls._image_url(story),
            published_at=cls._published_at(story.get("published-at")),
            body=cls._extract_body(story.get("cards")),
            tags=tag_names,
            source=cls.SOURCE,
            language=cls.LANGUAGE,
            scraped_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        )

    def _should_stop(self) -> str | None:
        if self.total_articles >= self.max_total_articles:
            return f"reached max_total_articles={self.max_total_articles}"

        if self.total_articles >= self.min_articles_before_ratio_check:
            ratio = self.old_articles / self.total_articles
            if ratio > self.max_old_article_ratio:
                return (
                    f"old-article ratio {ratio:.2%} exceeded "
                    f"max_old_article_ratio={self.max_old_article_ratio:.2%} "
                    f"(old={self.old_articles}, total={self.total_articles})"
                )

        return None

    def parse(self, response: scrapy.http.Response, offset: int):
        payload = response.json()
        items = payload.get("items", []) if isinstance(payload, dict) else []

        if not isinstance(items, list) or not items:
            self.stop_reason = "API returned no items"
            self.logger.info("TNIE crawl finished: %s", self.stop_reason)
            return

        for entry in items:
            if self.total_articles >= self.max_total_articles:
                self.stop_reason = self._should_stop()
                break

            story = entry.get("story") if isinstance(entry, dict) else None
            if not isinstance(story, dict):
                self.logger.warning(
                    "Skipping API item without a story object at offset=%d", offset
                )
                continue

            item = self._item_from_story(story)
            if item is None:
                self.logger.warning("Skipping story without a URL at offset=%d", offset)
                continue

            self.total_articles += 1
            if self._is_old(item.published_at):
                self.old_articles += 1

            yield item

            self.stop_reason = self._should_stop()
            if self.stop_reason:
                break

        if self.stop_reason:
            self.logger.info("TNIE crawl finished: %s", self.stop_reason)
            return

        yield self._api_request(offset + self.PAGE_SIZE)

    def closed(self, reason: str) -> None:
        ratio = self.old_articles / self.total_articles if self.total_articles else 0.0
        self.logger.info(
            "[Tamil Nadu] articles=%d old=%d old_ratio=%.2f%% stop_reason=%s",
            self.total_articles,
            self.old_articles,
            ratio * 100,
            self.stop_reason or reason,
        )
