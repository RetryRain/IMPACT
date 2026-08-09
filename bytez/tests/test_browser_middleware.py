from unittest.mock import MagicMock

from scrapy.http import Request

from bytez.browser import BROWSER_REQUEST_HEADERS, BROWSER_USER_AGENT
from bytez.middlewares import BrowserHeadersMiddleware


def test_applies_browser_headers_and_referer():
    middleware = BrowserHeadersMiddleware.from_crawler(MagicMock())
    request = Request("https://www.thehindu.com/news/national/article123.ece")

    middleware.process_request(request, spider=MagicMock())

    assert request.headers[b"User-Agent"] == BROWSER_USER_AGENT.encode("utf-8")
    for name, value in BROWSER_REQUEST_HEADERS.items():
        assert request.headers[name.lower().encode("utf-8")] == value.encode("utf-8")
    assert request.headers[b"Referer"] == b"https://www.thehindu.com/"


def test_does_not_override_existing_headers():
    middleware = BrowserHeadersMiddleware.from_crawler(MagicMock())
    request = Request(
        "https://timesofindia.indiatimes.com/world",
        headers={"User-Agent": "custom-agent", "Accept": "application/json"},
    )

    middleware.process_request(request, spider=MagicMock())

    assert request.headers[b"User-Agent"] == b"custom-agent"
    assert request.headers[b"Accept"] == b"application/json"
