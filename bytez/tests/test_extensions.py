from __future__ import annotations

from unittest.mock import MagicMock, patch

from bytez.extensions import CrawlProgressExtension


def _extension(**kwargs) -> CrawlProgressExtension:
    stats = MagicMock()
    stats.get_value.side_effect = lambda key, default=0: {
        "item_scraped_count": kwargs.get("items", 0),
        "response_received_count": kwargs.get("responses", 0),
    }.get(key, default)
    return CrawlProgressExtension(stats, heartbeat_seconds=0, item_step=10)


class TestCrawlProgressExtension:
    def test_spider_opened_logs_start_and_initial_heartbeat(self):
        extension = CrawlProgressExtension(
            MagicMock(),
            heartbeat_seconds=10,
            item_step=10,
        )
        spider = MagicMock()
        spider.name = "all_spiders"

        with patch("bytez.extensions.PROGRESS_LOGGER") as logger:
            with patch.object(extension, "_schedule_next_heartbeat") as schedule:
                extension.spider_opened(spider)
                assert logger.info.call_count == 2
                logger.info.assert_any_call("Crawl started: %s", "all_spiders")
                schedule.assert_called_once()

    def test_first_item_logs_title_and_source(self):
        extension = _extension(items=1)
        item = {"title": "Sample headline", "source": "The Hindu"}
        response = MagicMock(url="https://example.com/article")

        with patch("bytez.extensions.PROGRESS_LOGGER") as logger:
            extension.item_scraped(item, response, spider=MagicMock(name="all_spiders"))
            logger.info.assert_called_once_with(
                "First article scraped: %s (%s)",
                "Sample headline",
                "The Hindu",
            )

    def test_item_milestone_logs_every_step(self):
        extension = _extension(items=20)
        extension._started_at = 0.0
        item = {"title": "Another", "source": "TOI"}
        response = MagicMock(url="https://example.com/2")

        with patch("bytez.extensions.CrawlProgressExtension._elapsed_seconds", return_value=12.0):
            with patch("bytez.extensions.PROGRESS_LOGGER") as logger:
                extension.item_scraped(item, response, spider=MagicMock(name="all_spiders"))
                logger.info.assert_called_once_with(
                    "Progress: %d articles scraped (%.0fs elapsed)",
                    20,
                    12.0,
                )

    def test_spider_closed_cancels_heartbeat(self):
        extension = _extension()
        extension._heartbeat_call = MagicMock()
        extension._heartbeat_call.active.return_value = True

        extension.spider_closed(MagicMock(name="all_spiders"), "finished")

        extension._heartbeat_call.cancel.assert_called_once()
        assert extension._closed is True

    def test_heartbeat_tick_reschedules(self):
        extension = _extension()
        extension._spider_name = "all_spiders"

        with patch.object(extension, "_log_heartbeat") as log_heartbeat:
            with patch.object(extension, "_schedule_next_heartbeat") as schedule:
                extension._heartbeat_tick()
                log_heartbeat.assert_called_once_with("all_spiders")
                schedule.assert_called_once()
