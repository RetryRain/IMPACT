from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import ClassVar

import scrapy
from scrapy.exceptions import CloseSpider

from bytez.items import BytezItem


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

    # Kept for compatibility with anything (extensions, signal handlers,
    # etc.) that inspects spider.start_urls - actual crawl entry points
    # are driven by start_requests() below, not this list.
    start_urls: ClassVar[tuple[str, ...]] = (INDIA_FEED_URL, WORLD_START_URL)

    PROMO_MARKERS: ClassVar[tuple[str, ...]] = (
        "You Can Also Check:",
        "Stay updated with the latest",
        "Download the TOI App",
    )

    # --- Stop-condition configuration -------------------------------------
    # The crawl closes itself as soon as either of these is met. Counters
    # are shared across scopes (India + World), so the cap applies to the
    # crawl as a whole, not per scope.

    # 1) Hard cap on the total number of articles collected.
    MAX_TOTAL_ARTICLES: ClassVar[int] = 1000

    # 2) An article is considered "old" if it was published more than
    #    OLD_ARTICLE_MAX_AGE before the current time (evaluated at scrape
    #    time, using each article's "published_at" field). Once the share
    #    of old articles among everything collected so far exceeds
    #    MAX_OLD_ARTICLE_RATIO, the crawl stops - this is meant to detect
    #    that the spider has drifted from "top news" into stale/back-catalog
    #    content via related-article links.
    OLD_ARTICLE_MAX_AGE: ClassVar[timedelta] = timedelta(days=1)
    MAX_OLD_ARTICLE_RATIO: ClassVar[float] = 0.5

    # Don't apply the ratio check until at least this many articles have
    # been collected, so a small early batch of old articles can't trigger
    # a premature stop.
    MIN_ARTICLES_BEFORE_RATIO_CHECK: ClassVar[int] = 25

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_articles: int = 0
        self.old_articles: int = 0

    def start_requests(self):
        self.logger.debug("start_requests() entered - dispatching India + World crawls")
        yield scrapy.Request(self.INDIA_FEED_URL, callback=self.parse)
        yield scrapy.Request(self.WORLD_START_URL, callback=self.parse_world)

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
    def _parse_published_at(value: str | None) -> datetime | None:
        if not value:
            return None

        try:
            # Handle a trailing "Z" (Zulu/UTC) which fromisoformat rejects
            # on older Python versions.
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _is_old(self, published_at: str | None) -> bool:
        parsed = self._parse_published_at(published_at)

        if parsed is None:
            # Unknown age is not counted as old - we simply can't tell.
            return False

        now = datetime.now(UTC)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)

        return (now - parsed) > self.OLD_ARTICLE_MAX_AGE

    def _register_article(self, published_at: str | None) -> None:
        self.total_articles += 1

        if self._is_old(published_at):
            self.old_articles += 1

    def _should_stop(self) -> str | None:
        """Return a close reason if a stop condition has been met, else None."""
        if self.total_articles >= self.MAX_TOTAL_ARTICLES:
            return (
                f"reached MAX_TOTAL_ARTICLES={self.MAX_TOTAL_ARTICLES} "
                f"(collected={self.total_articles})"
            )

        if self.total_articles >= self.MIN_ARTICLES_BEFORE_RATIO_CHECK:
            ratio = self.old_articles / self.total_articles

            if ratio > self.MAX_OLD_ARTICLE_RATIO:
                return (
                    f"old-article ratio {ratio:.2%} exceeded "
                    f"MAX_OLD_ARTICLE_RATIO={self.MAX_OLD_ARTICLE_RATIO:.2%} "
                    f"(old={self.old_articles}, total={self.total_articles})"
                )

        return None

    def parse(self, response):
        for article in response.json():
            url = article.get("wu")

            if not url:
                continue

            # Skip videos, galleries, shorts, etc.
            if "/articleshow/" not in url:
                continue

            item = BytezItem(
                title=article.get("hl"),
                url=url,
                scope="India",
                summary=article.get("des"),
                source="The Times of India",
                language="en",
            )

            yield response.follow(
                url,
                callback=self.parse_article,
                cb_kwargs={"item": item},
            )

    def parse_world(self, response):
        """Entry point for the World section front page.

        Unlike the India feed (a JSON list of articles), this is an HTML
        page, so we don't have per-article metadata (headline/summary)
        up front - we just harvest article links off the page and let
        parse_article build the item from each article's own JSON-LD.
        """
        if self._should_stop() is not None:
            return

        for link in self.extract_article_links(response):
            yield response.follow(
                link,
                callback=self.parse_article,
                cb_kwargs={"scope": "World"},
            )

    def extract_article_links(self, response) -> set[str]:
        """Collect every in-page link that points to another TOI article.

        Any href containing '/articleshow/' is treated as an article link,
        the same filter already used against the JSON feed in ``parse``.
        This lets the spider discover and crawl articles that are only
        reachable via links embedded in other article pages (related
        stories, trending topics, etc.), not just the ones in the feed.
        """
        links: set[str] = set()

        for href in response.css("a::attr(href)").getall():
            if not href or "/articleshow/" not in href:
                continue

            links.add(response.urljoin(href))

        return links

    def parse_article(
        self,
        response,
        item: BytezItem | None = None,
        scope: str = "India",
    ):
        data = None

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
                    data = obj
                    break

        # Scope to use for this page and anything discovered from it: an
        # upstream item (from the India feed) already carries its scope,
        # otherwise fall back to whatever scope this request was tagged
        # with (e.g. "World" from parse_world).
        effective_scope = item.scope if item is not None else scope

        if data is None:
            self.logger.warning("Article JSON-LD not found: %s", response.url)
            # Still worth exploring links from this page even if we
            # couldn't parse the article itself, unless we're already
            # supposed to be stopping.
            if self._should_stop() is None:
                for link in self.extract_article_links(response):
                    if link != response.url:
                        yield response.follow(
                            link,
                            callback=self.parse_article,
                            cb_kwargs={"scope": effective_scope},
                        )
            return

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
                if isinstance(first, dict):
                    image = first.get("url")
                else:
                    image = first
            else:
                image = None

        author = data.get("author")

        if isinstance(author, dict):
            author = author.get("name")
        elif isinstance(author, list):
            author = ", ".join(
                a["name"] for a in author if isinstance(a, dict) and "name" in a
            )

        if item is None:
            # Discovered via an in-page link rather than the JSON feed, so
            # there's no upstream item yet - build one from the JSON-LD.
            item = BytezItem(
                title=data.get("headline"),
                url=response.url,
                scope=effective_scope,
                summary=data.get("description"),
                source="The Times of India",
                language="en",
            )

        item.author = author
        item.image = image
        item.published_at = data.get("datePublished")
        item.body = self.clean_body(data.get("articleBody"))
        item.tags = keywords
        item.scraped_at = datetime.now(UTC).replace(microsecond=0).isoformat()

        self._register_article(item.published_at)
        yield item

        close_reason = self._should_stop()

        if close_reason is not None:
            raise CloseSpider(close_reason)

        # Only keep expanding the crawl via in-page links while we're
        # still below both stop thresholds.
        for link in self.extract_article_links(response):
            if link == response.url:
                continue

            yield response.follow(
                link,
                callback=self.parse_article,
                cb_kwargs={"scope": item.scope},
            )