from unittest.mock import MagicMock

import pytest
from scrapy.exceptions import IgnoreRequest
from scrapy.http import Request

from bytez.middlewares import ScopeStopDownloaderMiddleware


def test_ignores_requests_for_stopped_scope():
    crawler = MagicMock()
    crawler.bytez_stopped_scope_keys = {"toi/India"}
    middleware = ScopeStopDownloaderMiddleware(crawler)
    request = Request(
        "https://example.com/article",
        meta={"bytez_scope_key": "toi/India"},
    )

    with pytest.raises(IgnoreRequest):
        middleware.process_request(request, spider=MagicMock())


def test_allows_requests_for_active_scope():
    crawler = MagicMock()
    crawler.bytez_stopped_scope_keys = {"toi/India"}
    middleware = ScopeStopDownloaderMiddleware(crawler)
    request = Request(
        "https://example.com/article",
        meta={"bytez_scope_key": "toi/World"},
    )

    assert middleware.process_request(request, spider=MagicMock()) is None
