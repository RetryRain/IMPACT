from urllib.parse import urlparse

from scrapy.exceptions import IgnoreRequest

from bytez.browser import BROWSER_REQUEST_HEADERS, BROWSER_USER_AGENT


class BrowserHeadersMiddleware:
    """Apply browser-like headers to every outgoing request."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        request.headers.setdefault(b"User-Agent", BROWSER_USER_AGENT.encode("utf-8"))
        for name, value in BROWSER_REQUEST_HEADERS.items():
            request.headers.setdefault(name.lower().encode("utf-8"), value.encode("utf-8"))

        parsed = urlparse(request.url)
        if parsed.scheme and parsed.netloc:
            origin = f"{parsed.scheme}://{parsed.netloc}/"
            request.headers.setdefault(b"Referer", origin.encode("utf-8"))

        return None


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
