from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import ClassVar
from urllib.parse import urlparse

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

    INDIA_SCOPE: ClassVar[str] = "India"
    WORLD_SCOPE: ClassVar[str] = "World"

    # All scopes the crawl is responsible for. The spider only closes once
    # every scope in this tuple has independently hit a stop condition.
    SCOPES: ClassVar[tuple[str, ...]] = (INDIA_SCOPE, WORLD_SCOPE)

    PROMO_MARKERS: ClassVar[tuple[str, ...]] = (
        "You Can Also Check:",
        "Stay updated with the latest",
        "Download the TOI App",
    )

    # --- Stop-condition configuration -------------------------------------
    # These thresholds are applied independently PER SCOPE (India and World
    # each get their own budget) rather than to a single shared total.

    # 1) Hard cap on the number of articles collected, per scope.
    MAX_TOTAL_ARTICLES: ClassVar[int] = 1000

    # 2) An article is considered "old" if it was published more than
    #    OLD_ARTICLE_MAX_AGE before the current time (evaluated at scrape
    #    time, using each article's "published_at" field). Once the share
    #    of old articles collected so far *within a scope* exceeds
    #    MAX_OLD_ARTICLE_RATIO, that scope stops expanding - this is meant
    #    to detect that the crawl has drifted from "top news" into
    #    stale/back-catalog content via related-article links.
    OLD_ARTICLE_MAX_AGE: ClassVar[timedelta] = timedelta(days=2)
    MAX_OLD_ARTICLE_RATIO: ClassVar[float] = 0.5

    # Don't apply the ratio check for a scope until at least this many
    # articles have been collected *for that scope*, so a small early
    # batch of old articles can't trigger a premature stop.
    MIN_ARTICLES_BEFORE_RATIO_CHECK: ClassVar[int] = 200

    # Hard cap on how many article links get followed from a single page.
    # Some pages (e.g. ones with a large "trending"/"top stories" widget)
    # can contain hundreds of matching links - without a cap, one such
    # page can single-handedly balloon the scheduler queue into a huge
    # backlog that then has to be drained (at DOWNLOAD_DELAY pace) even
    # after a scope has already hit its article cap. Kept deliberately
    # low: with MIN_ARTICLES_BEFORE_RATIO_CHECK=200, worst-case backlog
    # built up before a scope can even be detected as done is roughly
    # 200 * MAX_LINKS_PER_PAGE requests, so this value directly trades
    # off crawl breadth against how long the tail-end drain takes.
    MAX_LINKS_PER_PAGE: ClassVar[int] = 15

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_articles: dict[str, int] = {}
        self.old_articles: dict[str, int] = {}
        # scope -> reason string, populated once that scope's cap is hit.
        self.stopped_scopes: dict[str, str] = {}

    async def start(self):
        yield scrapy.Request(
            self.INDIA_FEED_URL,
            callback=self.parse,
        )

        yield scrapy.Request(
            self.WORLD_START_URL,
            callback=self.parse_world,
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

    def _register_article(self, scope: str, published_at: str | None) -> None:
        self.total_articles[scope] = self.total_articles.get(scope, 0) + 1

        if self._is_old(published_at):
            self.old_articles[scope] = self.old_articles.get(scope, 0) + 1

    def _should_stop(self, scope: str) -> str | None:
        """Return a close reason if `scope` has hit a stop condition."""
        total = self.total_articles.get(scope, 0)

        if total >= self.MAX_TOTAL_ARTICLES:
            return (
                f"[{scope}] reached MAX_TOTAL_ARTICLES={self.MAX_TOTAL_ARTICLES} "
                f"(collected={total})"
            )

        if total >= self.MIN_ARTICLES_BEFORE_RATIO_CHECK:
            old = self.old_articles.get(scope, 0)
            ratio = old / total

            if ratio > self.MAX_OLD_ARTICLE_RATIO:
                return (
                    f"[{scope}] old-article ratio {ratio:.2%} exceeded "
                    f"MAX_OLD_ARTICLE_RATIO={self.MAX_OLD_ARTICLE_RATIO:.2%} "
                    f"(old={old}, total={total})"
                )

        return None

    @staticmethod
    def _world_allows_url(url: str) -> bool:
        """For World-scope crawling, reject any URL whose path (everything
        after the domain) contains "india" - e.g. reject
        /business/india-business/... but allow /world/us/....
        Only the path is checked, so "indiatimes.com" in the domain itself
        is never a problem.
        """
        path = urlparse(url).path
        return "india" not in path.lower()

    def _filter_links_for_scope(self, links: set[str], scope: str) -> set[str]:
        if scope == self.WORLD_SCOPE:
            links = {link for link in links if self._world_allows_url(link)}

        if len(links) > self.MAX_LINKS_PER_PAGE:
            links = set(list(links)[: self.MAX_LINKS_PER_PAGE])

        return links

    def _handle_scope_stop(self, scope: str, reason: str) -> None:
        """Record that `scope` has stopped, closing the spider once every
        scope in SCOPES has independently stopped."""
        if scope in self.stopped_scopes:
            return

        self.stopped_scopes[scope] = reason
        self.logger.info("Scope finished: %s", reason)

        if set(self.stopped_scopes) >= set(self.SCOPES):
            combined = "; ".join(
                self.stopped_scopes[s] for s in self.SCOPES if s in self.stopped_scopes
            )
            raise CloseSpider(combined)

    def closed(self, reason: str) -> None:
        """Scrapy calls this automatically on spider shutdown. Logs a
        separate summary line per scope (India, World) rather than one
        combined total."""
        for scope in self.SCOPES:
            total = self.total_articles.get(scope, 0)
            old = self.old_articles.get(scope, 0)
            ratio = (old / total) if total else 0.0
            scope_reason = self.stopped_scopes.get(
                scope, "did not hit a stop condition"
            )

            self.logger.info(
                "[%s] articles=%d old=%d old_ratio=%.2f%% stop_reason=%s",
                scope,
                total,
                old,
                ratio * 100,
                scope_reason,
            )

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
                scope=self.INDIA_SCOPE,
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
        if self.WORLD_SCOPE in self.stopped_scopes:
            return

        links = self._filter_links_for_scope(
            self.extract_article_links(response), self.WORLD_SCOPE
        )

        for link in links:
            yield response.follow(
                link,
                callback=self.parse_article,
                cb_kwargs={"scope": self.WORLD_SCOPE},
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

            # Guard against malformed hrefs (e.g. a stray leading
            # character before what looks like a URL) that urljoin would
            # otherwise mangle into a garbage concatenated URL.
            if not (href.startswith("/") or href.lower().startswith("http")):
                continue

            links.add(response.urljoin(href))

        return links

    def parse_article(
        self,
        response,
        item: BytezItem | None = None,
        scope: str = "India",
    ):
        # Scope to use for this page and anything discovered from it: an
        # upstream item (from the India feed) already carries its scope,
        # otherwise fall back to whatever scope this request was tagged
        # with (e.g. "World" from parse_world).
        effective_scope = item.scope if item is not None else scope

        # This request may have been queued *before* effective_scope hit
        # its cap (large backlogs build up quickly since we only stop
        # adding new links, not the ones already scheduled). Drop it here,
        # before it gets counted, so a scope can't overshoot its cap by
        # however many requests happened to already be in the queue.
        if effective_scope in self.stopped_scopes:
            return

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

        if data is None:
            self.logger.warning("Article JSON-LD not found: %s", response.url)
            # Still worth exploring links from this page even if we
            # couldn't parse the article itself - effective_scope is
            # guaranteed not-yet-stopped here (checked at the top of this
            # method).
            links = self._filter_links_for_scope(
                self.extract_article_links(response), effective_scope
            )

            for link in links:
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

        self._register_article(item.scope, item.published_at)
        yield item

        stop_reason = self._should_stop(item.scope)

        if stop_reason is not None:
            # Stop expanding further into this scope; the other scope (if
            # still active) keeps crawling. The spider only actually
            # closes once every scope has stopped - see _handle_scope_stop.
            self._handle_scope_stop(item.scope, stop_reason)
            return

        # Only keep expanding the crawl via in-page links while this
        # scope is still below both of its stop thresholds.
        links = self._filter_links_for_scope(
            self.extract_article_links(response), item.scope
        )

        for link in links:
            if link == response.url:
                continue

            yield response.follow(
                link,
                callback=self.parse_article,
                cb_kwargs={"scope": item.scope},
            )
