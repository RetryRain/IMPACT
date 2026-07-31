import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scrapy import signals


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

        # Create logs directory if it doesn't exist
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

        self.report_file = self.logs_dir / "crawl_reports.log"
        self.json_file = self.logs_dir / "crawl_stats.jsonl"

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

        timestamp = datetime.now(
            timezone(timedelta(hours=5, minutes=30), name="IST")
        ).strftime("%Y-%m-%d %H:%M:%S %Z")

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
            + "=" * 60
        )

        # Log to Scrapy console
        spider.logger.info(report)

        # Append human-readable report
        with self.report_file.open("a", encoding="utf-8") as file:
            file.write(report + "\n")

        # Append machine-readable JSON
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
        }

        with self.json_file.open("a", encoding="utf-8") as file:
            json.dump(record, file)
            file.write("\n")
