from scrapy.exceptions import IgnoreRequest


class ScopeStopDownloaderMiddleware:
    """Skip downloads for scopes that have already hit a stop condition."""

    def __init__(self, crawler):
        self.crawler = crawler

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_request(self, request, spider):
        scope_key = request.meta.get("bytez_scope_key")
        stopped_keys = getattr(self.crawler, "bytez_stopped_scope_keys", None)
        if scope_key and stopped_keys is not None and scope_key in stopped_keys:
            raise IgnoreRequest(f"scope stopped: {scope_key}")
