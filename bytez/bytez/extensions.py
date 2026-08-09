from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from bytez.spiders.common import IST, ist_now_iso

from itemadapter import ItemAdapter
from scrapy import signals


BYTEZ_CRAWL_LOGGER = "bytez.crawl"
LOGS_DIR = Path("logs")
PROGRESS_LOGGER = logging.getLogger(BYTEZ_CRAWL_LOGGER)


class CrawlProgressExtension:
    """Emit brief console heartbeats so long crawls show visible activity."""

    def __init__(self, stats, *, heartbeat_seconds: float, item_step: int) -> None:
        self.stats = stats
        self.heartbeat_seconds = heartbeat_seconds
        self.item_step = max(1, item_step)
        self._heartbeat_call = None
        self._started_at: float | None = None
        self._spider_name: str | None = None
        self._closed = False

    @classmethod
    def from_crawler(cls, crawler):
        heartbeat_seconds = crawler.settings.getfloat(
            "BYTEZ_PROGRESS_HEARTBEAT_SECONDS", 10.0
        )
        item_step = crawler.settings.getint("BYTEZ_PROGRESS_ITEM_STEP", 10)
        extension = cls(
            crawler.stats,
            heartbeat_seconds=heartbeat_seconds,
            item_step=item_step,
        )
        crawler.signals.connect(extension.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(extension.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(extension.spider_closed, signal=signals.spider_closed)
        return extension

    def spider_opened(self, spider) -> None:
        from time import monotonic

        self._closed = False
        self._spider_name = spider.name
        self._started_at = monotonic()
        PROGRESS_LOGGER.info("Crawl started: %s", spider.name)
        if self.heartbeat_seconds > 0:
            self._log_heartbeat(spider.name)
            self._schedule_next_heartbeat()

    def item_scraped(self, item, response, spider) -> None:
        count = self.stats.get_value("item_scraped_count", 0)
        if count == 1:
            adapter = ItemAdapter(item)
            PROGRESS_LOGGER.info(
                "First article scraped: %s (%s)",
                adapter.get("title") or response.url,
                adapter.get("source") or spider.name,
            )
            return

        if count % self.item_step != 0:
            return

        elapsed = self._elapsed_seconds()
        PROGRESS_LOGGER.info(
            "Progress: %d articles scraped (%.0fs elapsed)",
            count,
            elapsed,
        )

    def spider_closed(self, spider, reason) -> None:
        self._closed = True
        if self._heartbeat_call is not None and self._heartbeat_call.active():
            self._heartbeat_call.cancel()

    def _schedule_next_heartbeat(self) -> None:
        if self._closed or self._spider_name is None or self.heartbeat_seconds <= 0:
            return

        from twisted.internet import reactor

        self._heartbeat_call = reactor.callLater(
            self.heartbeat_seconds,
            self._heartbeat_tick,
        )

    def _heartbeat_tick(self) -> None:
        if self._closed or self._spider_name is None:
            return
        self._log_heartbeat(self._spider_name)
        self._schedule_next_heartbeat()

    def _elapsed_seconds(self) -> float:
        from time import monotonic

        if self._started_at is None:
            return 0.0
        return monotonic() - self._started_at

    def _log_heartbeat(self, spider_name: str) -> None:
        items = self.stats.get_value("item_scraped_count", 0)
        responses = self.stats.get_value("response_received_count", 0)
        PROGRESS_LOGGER.info(
            "Crawl running: %s | articles=%d responses=%d elapsed=%.0fs",
            spider_name,
            items,
            responses,
            self._elapsed_seconds(),
        )


class ConsoleLogFilter(logging.Filter):
    """Keep console output minimal: warnings/errors plus brief bytez summaries."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.WARNING:
            return True
        if record.name.startswith("bytez.") and record.levelno >= logging.INFO:
            return True
        return False


class ProdLoggingExtension:
    """Route full crawl detail to logs/scrapy.log; keep stderr clean."""

    @classmethod
    def from_crawler(cls, crawler):
        extension = cls()
        extension._configure_progress_console_logger()
        crawler.signals.connect(extension.engine_started, signal=signals.engine_started)
        return extension

    def engine_started(self) -> None:
        LOGS_DIR.mkdir(exist_ok=True)
        self._configure_scrapy_console_filter()

    def _configure_progress_console_logger(self) -> None:
        progress_logger = logging.getLogger(BYTEZ_CRAWL_LOGGER)
        progress_logger.setLevel(logging.INFO)
        progress_logger.propagate = False

        for handler in progress_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                return

        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        progress_logger.addHandler(handler)

    def _configure_scrapy_console_filter(self) -> None:
        console_filter = ConsoleLogFilter()
        for logger_name in ("", "scrapy"):
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers:
                if not isinstance(handler, logging.StreamHandler):
                    continue
                if handler.stream not in (sys.stderr, sys.stdout):
                    continue
                handler.addFilter(console_filter)
                handler.setLevel(logging.INFO)


class ItemFileLogExtension:
    """Persist every scraped article to logs/crawl_items.jsonl."""

    def __init__(self) -> None:
        self._file = None

    @classmethod
    def from_crawler(cls, crawler):
        extension = cls()
        crawler.signals.connect(extension.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(extension.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(extension.spider_closed, signal=signals.spider_closed)
        return extension

    def spider_opened(self, spider) -> None:
        LOGS_DIR.mkdir(exist_ok=True)
        items_file = LOGS_DIR / "crawl_items.jsonl"
        self._file = items_file.open("a", encoding="utf-8")

    def item_scraped(self, item, response, spider) -> None:
        if self._file is None:
            return

        record = dict(ItemAdapter(item))
        record["_scraped_at"] = ist_now_iso()
        record["_spider"] = spider.name
        record["_source_url"] = response.url
        json.dump(record, self._file, ensure_ascii=False)
        self._file.write("\n")

    def spider_closed(self, spider, reason) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None


class CrawlSummaryExtension:
    @classmethod
    def from_crawler(cls, crawler):
        extension = cls(crawler.stats)

        crawler.signals.connect(
            extension.spider_closed,
            signal=signals.spider_closed,
        )

        return extension

    def __init__(self, stats):
        self.stats = stats
        self.report_file = LOGS_DIR / "crawl_reports.log"
        self.json_file = LOGS_DIR / "crawl_stats.jsonl"

    def _scope_summaries(self, stats: dict) -> list[str]:
        scope_names: set[str] = set()
        for key in stats:
            if key.startswith("scope/") and key.endswith("/items"):
                scope_names.add(key.removeprefix("scope/").removesuffix("/items"))

        lines: list[str] = []
        for scope in sorted(scope_names):
            fresh = stats.get(f"scope/{scope}/fresh_items", 0)
            stale = stats.get(f"scope/{scope}/stale_items", 0)
            unknown = stats.get(f"scope/{scope}/unknown_date_items", 0)
            stop_reason = stats.get(f"scope/{scope}/stop_reason", "n/a")
            lines.append(
                f"  [{scope}] fresh={fresh} stale={stale} unknown={unknown} "
                f"stop={stop_reason}"
            )
        return lines

    def spider_closed(self, spider, reason):
        stats = self.stats.get_stats()

        items = stats.get("item_scraped_count", 0)
        dropped = stats.get("item_dropped_count", 0)

        requests = stats.get("downloader/request_count", 0)
        responses = stats.get("response_received_count", 0)

        elapsed = stats.get("elapsed_time_seconds", 0.0)

        bytes_downloaded = stats.get(
            "downloader/response_bytes",
            0,
        )
        mb_downloaded = bytes_downloaded / (1024 * 1024)

        articles_per_sec = items / elapsed if elapsed else 0

        drop_rate = dropped / (items + dropped) * 100 if (items + dropped) else 0

        avg_response_size = mb_downloaded / responses if responses else 0

        http_200 = stats.get(
            "downloader/response_status_count/200",
            0,
        )

        http_404 = stats.get(
            "downloader/response_status_count/404",
            0,
        )

        http_500 = stats.get(
            "downloader/response_status_count/500",
            0,
        )

        timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %Z")

        scope_lines = self._scope_summaries(stats)
        scope_block = "\n".join(scope_lines) if scope_lines else "  (no scope stats)"

        report = (
            "\n"
            + "=" * 60
            + "\n"
            + f"Timestamp             : {timestamp}\n"
            + f"Spider                : {spider.name}\n"
            + f"Articles scraped      : {items}\n"
            + f"Duplicates dropped    : {dropped}\n"
            + f"Drop rate             : {drop_rate:.2f}%\n"
            + f"Requests              : {requests}\n"
            + f"Responses             : {responses}\n"
            + f"Bytes downloaded      : {mb_downloaded:.2f} MB\n"
            + f"Average response size : {avg_response_size:.3f} MB\n"
            + f"Elapsed time          : {elapsed:.2f} s\n"
            + f"Articles/sec          : {articles_per_sec:.2f}\n"
            + f"HTTP 200              : {http_200}\n"
            + f"HTTP 404              : {http_404}\n"
            + f"HTTP 500              : {http_500}\n"
            + f"Finish reason         : {reason}\n"
            + "Scope summaries       :\n"
            + scope_block
            + "\n"
            + "=" * 60
        )

        LOGS_DIR.mkdir(exist_ok=True)

        logging.getLogger(BYTEZ_CRAWL_LOGGER).info(
            "Crawl finished: %s | articles=%d dropped=%d elapsed=%.1fs reason=%s",
            spider.name,
            items,
            dropped,
            elapsed,
            reason,
        )

        with self.report_file.open("a", encoding="utf-8") as file:
            file.write(report + "\n")

        record = {
            "timestamp": timestamp,
            "spider": spider.name,
            "articles_scraped": items,
            "duplicates_dropped": dropped,
            "drop_rate": round(drop_rate, 2),
            "requests": requests,
            "responses": responses,
            "bytes_downloaded": bytes_downloaded,
            "elapsed_seconds": round(elapsed, 2),
            "articles_per_second": round(articles_per_sec, 2),
            "http_200": http_200,
            "http_404": http_404,
            "http_500": http_500,
            "finish_reason": reason,
            "scope_summaries": scope_lines,
        }

        with self.json_file.open("a", encoding="utf-8") as file:
            json.dump(record, file)
            file.write("\n")
