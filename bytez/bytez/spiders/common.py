from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from scrapy.exceptions import CloseSpider

if TYPE_CHECKING:
    from scrapy import Spider
    from scrapy.statscollectors import StatsCollector


@dataclass(frozen=True)
class SpiderLimits:
    max_total_articles: int
    old_article_max_age: timedelta
    max_old_article_ratio: float
    min_articles_before_ratio_check: int
    max_published_age_hours: int


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


def parse_spider_limits(
    *,
    max_total_articles: str | None,
    old_article_max_age_days: str | None,
    max_old_article_ratio: str | None,
    min_articles_before_ratio_check: str | None,
    max_published_age_hours: str | None = None,
    defaults: SpiderLimits,
) -> SpiderLimits:
    return SpiderLimits(
        max_total_articles=_positive_int(
            max_total_articles, defaults.max_total_articles
        ),
        old_article_max_age=timedelta(
            days=_positive_float(
                old_article_max_age_days,
                defaults.old_article_max_age.total_seconds() / 86_400,
            )
        ),
        max_old_article_ratio=_ratio(
            max_old_article_ratio, defaults.max_old_article_ratio
        ),
        min_articles_before_ratio_check=_positive_int(
            min_articles_before_ratio_check,
            defaults.min_articles_before_ratio_check,
            allow_zero=True,
        ),
        max_published_age_hours=_positive_int(
            max_published_age_hours,
            defaults.max_published_age_hours,
            allow_zero=True,
        ),
    )


IST = timezone(timedelta(hours=5, minutes=30))


def to_ist_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=IST)
    return value.astimezone(IST).replace(microsecond=0).isoformat()


def ist_now_iso() -> str:
    return to_ist_iso(datetime.now(IST))


def utc_now_iso() -> str:
    """Backward-compatible alias; timestamps are stored in IST."""
    return ist_now_iso()


def parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def format_published_at(value: str | None) -> str | None:
    parsed = parse_iso_timestamp(value)
    if parsed is None:
        return None
    return to_ist_iso(parsed)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value


def is_old_article(
    published_at: str | None, *, max_age: timedelta
) -> bool:
    parsed = parse_iso_timestamp(published_at)
    if parsed is None:
        return False
    return (datetime.now(IST) - _ensure_aware(parsed).astimezone(IST)) > max_age


def is_within_published_window(
    published_at: str | None, *, max_age: timedelta
) -> bool:
    parsed = parse_iso_timestamp(published_at)
    if parsed is None:
        return False
    return (datetime.now(IST) - _ensure_aware(parsed).astimezone(IST)) <= max_age


def bounded_links(
    links: Iterable[str],
    cap: int,
    *,
    filter_fn: Callable[[str], bool] | None = None,
) -> list[str]:
    if filter_fn is None:
        unique = {link for link in links if link}
    else:
        unique = {link for link in links if link and filter_fn(link)}
    return sorted(unique)[:cap]


def make_scope_meta(spider_name: str, scope: str) -> dict[str, str]:
    return {"bytez_scope_key": f"{spider_name}/{scope}"}


class ScopeTracker:
    def __init__(
        self,
        limits: SpiderLimits,
        *,
        stats: StatsCollector | None = None,
        logger: Any = None,
        close_on_all_scopes: bool = True,
        scope_prefix: str = "",
        stopped_scope_sink: set[str] | None = None,
    ) -> None:
        self.limits = limits
        self.stats = stats
        self.logger = logger
        self.close_on_all_scopes = close_on_all_scopes
        self.scope_prefix = scope_prefix
        self.stopped_scope_sink = stopped_scope_sink
        self.fresh_articles: dict[str, int] = {}
        self.stale_articles: dict[str, int] = {}
        self.unknown_articles: dict[str, int] = {}
        self.total_articles: dict[str, int] = {}
        self.old_articles: dict[str, int] = {}
        self.stopped_scopes: dict[str, str] = {}

    def scope_key(self, scope: str) -> str:
        if self.scope_prefix:
            return f"{self.scope_prefix}/{scope}"
        return scope

    def is_stopped(self, scope: str) -> bool:
        return scope in self.stopped_scopes

    def encounters(self, scope: str) -> int:
        return (
            self.fresh_articles.get(scope, 0)
            + self.stale_articles.get(scope, 0)
            + self.unknown_articles.get(scope, 0)
        )

    def evaluate(self, scope: str, published_at: str | None) -> bool:
        if self.limits.max_published_age_hours == 0:
            return self._evaluate_legacy(scope, published_at)

        max_age = timedelta(hours=self.limits.max_published_age_hours)
        if is_within_published_window(published_at, max_age=max_age):
            self.fresh_articles[scope] = self.fresh_articles.get(scope, 0) + 1
            self.total_articles[scope] = self.fresh_articles[scope]
            if self.stats is not None:
                self.stats.inc_value(f"scope/{scope}/items")
                self.stats.inc_value(f"scope/{scope}/fresh_items")
            return True

        if parse_iso_timestamp(published_at) is None:
            self.unknown_articles[scope] = self.unknown_articles.get(scope, 0) + 1
            if self.stats is not None:
                self.stats.inc_value(f"scope/{scope}/unknown_date_items")
            return False

        self.stale_articles[scope] = self.stale_articles.get(scope, 0) + 1
        if self.stats is not None:
            self.stats.inc_value(f"scope/{scope}/stale_items")
        return False

    def _evaluate_legacy(self, scope: str, published_at: str | None) -> bool:
        self.fresh_articles[scope] = self.fresh_articles.get(scope, 0) + 1
        self.total_articles[scope] = self.fresh_articles[scope]
        if self.stats is not None:
            self.stats.inc_value(f"scope/{scope}/items")
            self.stats.inc_value(f"scope/{scope}/fresh_items")

        if is_old_article(published_at, max_age=self.limits.old_article_max_age):
            self.old_articles[scope] = self.old_articles.get(scope, 0) + 1
            if self.stats is not None:
                self.stats.inc_value(f"scope/{scope}/old_items")
        return True

    def register(self, scope: str, published_at: str | None) -> None:
        self.evaluate(scope, published_at)

    def should_stop(self, scope: str) -> str | None:
        fresh = self.fresh_articles.get(scope, 0)
        if fresh >= self.limits.max_total_articles:
            return f"reached max_total_articles={self.limits.max_total_articles}"

        if self.limits.max_published_age_hours == 0:
            total = self.fresh_articles.get(scope, 0)
            if total >= self.limits.min_articles_before_ratio_check:
                old = self.old_articles.get(scope, 0)
                ratio = old / total
                if ratio > self.limits.max_old_article_ratio:
                    return (
                        f"old-article ratio {ratio:.2%} exceeded "
                        f"max_old_article_ratio={self.limits.max_old_article_ratio:.2%} "
                        f"(old={old}, total={total})"
                    )
            return None

        encounters = self.encounters(scope)
        if encounters >= self.limits.min_articles_before_ratio_check:
            stale = self.stale_articles.get(scope, 0)
            unknown = self.unknown_articles.get(scope, 0)
            ratio = (stale + unknown) / encounters
            if ratio > self.limits.max_old_article_ratio:
                return (
                    f"stale-article ratio {ratio:.2%} exceeded "
                    f"max_old_article_ratio={self.limits.max_old_article_ratio:.2%} "
                    f"(stale={stale}, unknown={unknown}, encounters={encounters})"
                )
        return None

    def stop(self, scope: str, reason: str) -> bool:
        if scope in self.stopped_scopes:
            return False
        self.stopped_scopes[scope] = reason
        if self.stats is not None:
            self.stats.set_value(f"scope/{scope}/stop_reason", reason)
        if self.stopped_scope_sink is not None:
            self.stopped_scope_sink.add(self.scope_key(scope))
        if self.logger is not None:
            self.logger.debug("%s crawl finished: %s", scope, reason)
        return True

    def all_stopped(self, scopes: tuple[str, ...]) -> bool:
        return set(self.stopped_scopes) >= set(scopes)

    def maybe_close_spider(self, scopes: tuple[str, ...]) -> None:
        if self.all_stopped(scopes):
            combined = "; ".join(
                self.stopped_scopes[s] for s in scopes if s in self.stopped_scopes
            )
            raise CloseSpider(combined)

    def handle_scope_stop(self, scope: str, reason: str, scopes: tuple[str, ...]) -> None:
        if self.stop(scope, reason) and self.close_on_all_scopes:
            self.maybe_close_spider(scopes)

    def log_scope_summary(self, scope: str, fallback_reason: str) -> None:
        if self.logger is None:
            return
        fresh = self.fresh_articles.get(scope, 0)
        stale = self.stale_articles.get(scope, 0)
        unknown = self.unknown_articles.get(scope, 0)
        encounters = fresh + stale + unknown
        stale_ratio = (stale + unknown) / encounters if encounters else 0.0
        self.logger.debug(
            "[%s] fresh=%d stale=%d unknown=%d stale_ratio=%.2f%% stop_reason=%s",
            scope,
            fresh,
            stale,
            unknown,
            stale_ratio * 100,
            self.stopped_scopes.get(scope, fallback_reason),
        )


def scope_errback(
    spider: Spider,
    tracker: ScopeTracker,
    scope: str,
    scopes: tuple[str, ...],
    *,
    label: str = "request",
):
    def _errback(failure):
        request = failure.request
        url = request.url if request is not None else "unknown"
        detail = failure.getErrorMessage()
        spider.logger.error(
            "[%s] %s failed for %s: %s",
            scope,
            label,
            url,
            detail,
        )
        tracker.handle_scope_stop(scope, f"request failed: {detail}", scopes)

    return _errback
