from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from html import unescape
import re
from typing import Any, ClassVar
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import scrapy
from scrapy.selector import Selector

from bytez.items import BytezItem
from bytez.spiders.common import (
    ScopeTracker,
    SpiderLimits,
    parse_spider_limits,
    scope_errback,
    make_scope_meta,
    ist_now_iso,
    to_ist_iso,
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
    CF_IMAGES_HOST: ClassVar[str] = "cf-images.assettype.com"
    CF_IMAGES_BASE: ClassVar[str] = "https://cf-images.assettype.com/"
    CF_IMAGE_WIDTH: ClassVar[int] = 1200

    MAX_TOTAL_ARTICLES: ClassVar[int] = 1000
    OLD_ARTICLE_MAX_AGE: ClassVar[timedelta] = timedelta(days=1)
    MAX_OLD_ARTICLE_RATIO: ClassVar[float] = 0.5
    MIN_ARTICLES_BEFORE_RATIO_CHECK: ClassVar[int] = 200
    MAX_PUBLISHED_AGE_HOURS: ClassVar[int] = 24

    DEFAULT_LIMITS: ClassVar[SpiderLimits] = SpiderLimits(
        max_total_articles=MAX_TOTAL_ARTICLES,
        old_article_max_age=OLD_ARTICLE_MAX_AGE,
        max_old_article_ratio=MAX_OLD_ARTICLE_RATIO,
        min_articles_before_ratio_check=MIN_ARTICLES_BEFORE_RATIO_CHECK,
        max_published_age_hours=MAX_PUBLISHED_AGE_HOURS,
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
            meta=make_scope_meta(self.name, scope),
            cb_kwargs={"scope": scope, "api_url": api_url, "offset": offset},
        )

    @staticmethod
    def _published_at(value: object) -> str | None:
        if not isinstance(value, (int, float)):
            return None
        try:
            return to_ist_iso(
                datetime.fromtimestamp(value / 1000, tz=timezone.utc)
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

    @staticmethod
    def _absolute_https_url(url: str) -> str:
        stripped = url.strip()
        if stripped.startswith("//"):
            return f"https:{stripped}"
        return stripped

    @classmethod
    def _is_cf_images_url(cls, url: str) -> bool:
        return cls.CF_IMAGES_HOST in cls._absolute_https_url(url)

    @classmethod
    def _parse_srcset(cls, srcset: str) -> str | None:
        decoded = unescape(srcset.strip())
        candidates: list[tuple[int, str]] = []

        for part in decoded.split(","):
            piece = part.strip()
            if not piece:
                continue

            match = re.search(r"\s+(\d+)(w|x)\s*$", piece)
            if match:
                width = int(match.group(1))
                if match.group(2) == "x":
                    width *= 1000
                url = piece[: match.start()].strip()
            else:
                width = 0
                url = piece

            if url:
                candidates.append((width, cls._absolute_https_url(url)))

        if not candidates:
            return None

        return max(candidates, key=lambda candidate: candidate[0])[1]

    @classmethod
    def _upgrade_cf_image_url(cls, url: str) -> str | None:
        if not url or not url.strip():
            return None

        candidate = url.strip()
        if "," in candidate and "w" in candidate:
            parsed = cls._parse_srcset(candidate)
            if parsed:
                candidate = parsed

        normalized = cls._absolute_https_url(candidate)
        if not cls._is_cf_images_url(normalized):
            return normalized

        parsed = urlparse(normalized)
        params = dict(parse_qsl(parsed.query))
        params["w"] = str(cls.CF_IMAGE_WIDTH)
        params.setdefault("auto", "format,compress")
        params.setdefault("fit", "max")
        query = urlencode(params)
        return urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, "", query, "")
        )

    @classmethod
    def _cf_images_url_from_s3_key(cls, key: str) -> str:
        encoded_path = quote(key.lstrip("/"), safe="")
        query = urlencode(
            {
                "w": cls.CF_IMAGE_WIDTH,
                "auto": "format,compress",
                "fit": "max",
            }
        )
        return f"{cls.CF_IMAGES_BASE}{encoded_path}?{query}"

    @classmethod
    def _image_url(cls, story: dict[str, object]) -> str | None:
        metadata = story.get("hero-image-metadata")
        original_url: str | None = None
        if isinstance(metadata, dict):
            raw = metadata.get("original-url")
            if isinstance(raw, str) and raw.strip():
                original_url = raw.strip()

        s3_key = story.get("hero-image-s3-key")
        key = s3_key.strip() if isinstance(s3_key, str) and s3_key.strip() else None

        if original_url:
            absolute = cls._absolute_https_url(original_url)
            if cls._is_cf_images_url(absolute) or (
                "," in original_url and "w" in original_url
            ):
                return cls._upgrade_cf_image_url(original_url)
            if "d3lzcn6mbbadaf.cloudfront.net" in absolute:
                if key:
                    return cls._cf_images_url_from_s3_key(key)
                return None

        if key:
            return cls._cf_images_url_from_s3_key(key)

        if original_url:
            return cls._absolute_https_url(original_url)

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
            scraped_at=ist_now_iso(),
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

        page_had_fresh = False

        for entry in items:
            if self.tracker.fresh_articles.get(scope, 0) >= self.limits.max_total_articles:
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

            if self.tracker.evaluate(scope, item.published_at):
                yield item
                page_had_fresh = True

            stop_reason = self.tracker.should_stop(scope)
            if stop_reason:
                self.tracker.handle_scope_stop(scope, stop_reason, self.SCOPES)
                break

        if self.tracker.is_stopped(scope):
            return

        if items and not page_had_fresh:
            self.tracker.handle_scope_stop(
                scope, "pagination reached stale content", self.SCOPES
            )
            return

        yield self._api_request(scope, api_url, offset + self.PAGE_SIZE)

    def closed(self, reason: str) -> None:
        for scope in self.SCOPES:
            self.tracker.log_scope_summary(scope, reason)
