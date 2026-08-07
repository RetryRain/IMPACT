from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from scrapy.exceptions import CloseSpider

from bytez.spiders.common import (
    ScopeTracker,
    SpiderLimits,
    bounded_links,
    format_published_at,
    is_old_article,
    is_within_published_window,
    parse_iso_timestamp,
    parse_spider_limits,
    utc_now_iso,
)


def _default_limits(**overrides) -> SpiderLimits:
    return SpiderLimits(
        max_total_articles=overrides.get("max_total_articles", 1000),
        old_article_max_age=overrides.get("old_article_max_age", timedelta(days=1)),
        max_old_article_ratio=overrides.get("max_old_article_ratio", 0.5),
        min_articles_before_ratio_check=overrides.get(
            "min_articles_before_ratio_check", 200
        ),
        max_published_age_hours=overrides.get("max_published_age_hours", 24),
    )


class TestParseSpiderLimits:
    def test_uses_defaults_when_args_missing(self):
        defaults = _default_limits()
        limits = parse_spider_limits(
            max_total_articles=None,
            old_article_max_age_days=None,
            max_old_article_ratio=None,
            min_articles_before_ratio_check=None,
            max_published_age_hours=None,
            defaults=defaults,
        )
        assert limits == defaults

    def test_overrides_from_string_args(self):
        defaults = _default_limits()
        limits = parse_spider_limits(
            max_total_articles="25",
            old_article_max_age_days="3",
            max_old_article_ratio="0.25",
            min_articles_before_ratio_check="0",
            max_published_age_hours="12",
            defaults=defaults,
        )
        assert limits.max_total_articles == 25
        assert limits.old_article_max_age == timedelta(days=3)
        assert limits.max_old_article_ratio == 0.25
        assert limits.min_articles_before_ratio_check == 0
        assert limits.max_published_age_hours == 12


class TestTimestamps:
    def test_utc_now_iso_has_seconds_precision(self):
        value = utc_now_iso()
        assert value.endswith("+00:00")
        assert "." not in value

    def test_parse_iso_timestamp_handles_zulu(self):
        parsed = parse_iso_timestamp("2024-01-01T12:00:00Z")
        assert parsed == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_format_published_at_normalizes_to_utc_seconds(self):
        formatted = format_published_at("2024-02-15T08:30:00+05:30")
        assert formatted == "2024-02-15T03:00:00+00:00"

    def test_is_old_article_treats_naive_as_utc(self):
        old = (datetime.now(timezone.utc) - timedelta(days=5)).replace(microsecond=0)
        assert is_old_article(old.isoformat(), max_age=timedelta(days=1))

    def test_is_within_published_window_accepts_recent(self):
        recent = datetime.now(timezone.utc).isoformat()
        assert is_within_published_window(recent, max_age=timedelta(hours=24))

    def test_is_within_published_window_rejects_stale_and_missing(self):
        stale = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        assert not is_within_published_window(stale, max_age=timedelta(hours=24))
        assert not is_within_published_window(None, max_age=timedelta(hours=24))


class TestBoundedLinks:
    def test_returns_sorted_unique_links_capped(self):
        links = bounded_links(
            {"https://b.example/a", "https://a.example/a", "https://c.example/a"},
            2,
        )
        assert links == ["https://a.example/a", "https://b.example/a"]

    def test_applies_filter_fn(self):
        links = bounded_links(
            [
                "https://example.com/world/1",
                "https://example.com/india/1",
                "https://example.com/world/2",
            ],
            10,
            filter_fn=lambda url: "india" not in url,
        )
        assert links == [
            "https://example.com/world/1",
            "https://example.com/world/2",
        ]


class TestScopeTracker:
    def _tracker(self, **overrides) -> ScopeTracker:
        close_on_all_scopes = overrides.pop("close_on_all_scopes", True)
        limits = _default_limits(**overrides)
        stats = MagicMock()
        logger = MagicMock()
        return ScopeTracker(
            limits,
            stats=stats,
            logger=logger,
            close_on_all_scopes=close_on_all_scopes,
        )

    def test_evaluate_fresh_stale_and_unknown(self):
        tracker = self._tracker(max_published_age_hours=24)
        fresh = datetime.now(timezone.utc).isoformat()
        stale = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

        assert tracker.evaluate("India", fresh) is True
        assert tracker.evaluate("India", stale) is False
        assert tracker.evaluate("India", None) is False

        assert tracker.fresh_articles["India"] == 1
        assert tracker.stale_articles["India"] == 1
        assert tracker.unknown_articles["India"] == 1

    def test_article_cap_uses_fresh_only(self):
        tracker = self._tracker(max_total_articles=2, max_published_age_hours=24)
        fresh = datetime.now(timezone.utc).isoformat()
        stale = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

        tracker.evaluate("India", stale)
        tracker.evaluate("India", stale)
        tracker.evaluate("India", fresh)
        assert tracker.should_stop("India") is None

        tracker.evaluate("India", fresh)
        reason = tracker.should_stop("India")
        assert reason == "reached max_total_articles=2"

    def test_stale_ratio_stop_reason(self):
        tracker = self._tracker(
            max_total_articles=10,
            max_old_article_ratio=0.5,
            min_articles_before_ratio_check=2,
            max_published_age_hours=24,
        )
        stale = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        tracker.evaluate("India", stale)
        tracker.evaluate("India", stale)
        reason = tracker.should_stop("India")
        assert reason is not None
        assert "stale-article ratio" in reason

    def test_legacy_mode_register_counts_all_items(self):
        tracker = self._tracker(max_published_age_hours=0)
        old = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        tracker.register("India", old)
        tracker.stats.inc_value.assert_any_call("scope/India/items")
        tracker.stats.inc_value.assert_any_call("scope/India/old_items")

    def test_maybe_close_spider_raises_when_all_scopes_stopped(self):
        tracker = self._tracker()
        tracker.stop("India", "feed exhausted")
        with pytest.raises(CloseSpider):
            tracker.maybe_close_spider(("India", "World"))
        tracker.stop("World", "listing exhausted")
        with pytest.raises(CloseSpider):
            tracker.maybe_close_spider(("India", "World"))

    def test_handle_scope_stop_skips_close_when_disabled(self):
        tracker = self._tracker(close_on_all_scopes=False)
        tracker.handle_scope_stop("India", "feed exhausted", ("India", "World"))
        tracker.handle_scope_stop("World", "listing exhausted", ("India", "World"))
        assert tracker.all_stopped(("India", "World"))

    def test_log_scope_summary_format(self):
        tracker = self._tracker()
        fresh = datetime.now(timezone.utc).isoformat()
        tracker.evaluate("India", fresh)
        tracker.stop("India", "feed exhausted")
        tracker.log_scope_summary("India", "shutdown")
        tracker.logger.info.assert_called_with(
            "[%s] fresh=%d stale=%d unknown=%d stale_ratio=%.2f%% stop_reason=%s",
            "India",
            1,
            0,
            0,
            0.0,
            "feed exhausted",
        )
