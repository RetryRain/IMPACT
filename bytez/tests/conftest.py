from __future__ import annotations

import json
from pathlib import Path

import pytest
from scrapy.http import HtmlResponse, JsonResponse, Request, TextResponse

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(*parts: str) -> str:
    return (FIXTURES_DIR.joinpath(*parts)).read_text(encoding="utf-8")


def load_json_fixture(*parts: str):
    return json.loads(load_fixture(*parts))


@pytest.fixture
def make_response():
    def _make_response(
        url: str,
        body: str | bytes,
        *,
        response_class=TextResponse,
        request_meta: dict | None = None,
    ):
        request = Request(url=url, meta=request_meta or {})
        if isinstance(body, str):
            body = body.encode("utf-8")
        return response_class(url=url, body=body, request=request)

    return _make_response


@pytest.fixture
def make_html_response(make_response):
    def _make_html(url: str, html: str, *, request_meta: dict | None = None):
        return make_response(
            url, html, response_class=HtmlResponse, request_meta=request_meta
        )

    return _make_html


@pytest.fixture
def make_json_response(make_response):
    def _make_json(url: str, payload, *, request_meta: dict | None = None):
        body = json.dumps(payload).encode("utf-8")
        request = Request(url=url, meta=request_meta or {})
        return JsonResponse(url=url, body=body, request=request)

    return _make_json
