import json

import httpx
import pytest
from pydantic import ValidationError

from clustering.synthesis.openrouter_client import (
    OpenRouterClient,
    StructuredOutputError,
    SynthesisError,
)
from clustering.synthesis.prompt import (
    SynthesisResult,
    build_user_message,
    compact_cluster_payload,
)


def test_compact_cluster_payload_truncates_body(monkeypatch):
    monkeypatch.setenv("SYNTHESIS_BODY_CHAR_LIMIT", "10")
    from clustering.config import get_settings

    get_settings.cache_clear()

    payload = {
        "cluster_id": "abc",
        "scope": "India",
        "article_count": 1,
        "articles": [
            {
                "source": "The Hindu",
                "title": "Title",
                "url": "https://example.com/a",
                "summary": "Summary",
                "body": "x" * 50,
                "published_at": "2026-08-05T12:00:00+05:30",
            }
        ],
    }

    compact = compact_cluster_payload(payload)
    assert len(compact["articles"][0]["body"]) == 10
    assert "author" not in compact["articles"][0]


def test_synthesis_result_requires_rewrite_fields():
    with pytest.raises(ValidationError):
        SynthesisResult(
            action="rewrite",
            drop_reason=None,
            title="Only title",
            summary=None,
            body=None,
        )


def test_synthesis_result_requires_drop_reason():
    with pytest.raises(ValidationError):
        SynthesisResult(
            action="drop",
            drop_reason=None,
            title=None,
            summary=None,
            body=None,
        )


def test_build_user_message_contains_cluster_json():
    payload = {
        "cluster_id": "abc",
        "scope": "India",
        "article_count": 1,
        "articles": [],
    }
    message = build_user_message(payload)
    assert "cluster_id" in message
    assert "abc" in message


def _rewrite_response() -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "rewrite",
                            "drop_reason": None,
                            "title": "Rewritten",
                            "summary": "Short summary",
                            "body": "Full body",
                        }
                    )
                }
            }
        ]
    }


def test_openrouter_client_parses_structured_output():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/chat/completions":
            body = json.loads(request.content.decode())
            assert body["model"] == "test-model"
            assert body["response_format"]["type"] == "json_schema"
            assert len(body["messages"]) == 2
            return httpx.Response(200, json=_rewrite_response())
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://test")
    openrouter = OpenRouterClient(
        api_key="test-key",
        base_url="http://test",
        model="test-model",
        client=client,
    )

    result = openrouter.synthesize_cluster(
        {
            "cluster_id": "abc",
            "scope": "India",
            "article_count": 1,
            "articles": [],
        }
    )
    assert result.action == "rewrite"
    assert result.title == "Rewritten"


def test_openrouter_client_strips_markdown_fences():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                "```json\n"
                                + json.dumps(
                                    {
                                        "action": "rewrite",
                                        "drop_reason": None,
                                        "title": "Rewritten",
                                        "summary": "Short summary",
                                        "body": "Full body",
                                    }
                                )
                                + "\n```"
                            )
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://test")
    openrouter = OpenRouterClient(api_key="test-key", client=client)
    result = openrouter.synthesize_cluster({"cluster_id": "abc", "articles": []})
    assert result.title == "Rewritten"


def test_openrouter_client_raises_on_invalid_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not json"}}]},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://test")
    openrouter = OpenRouterClient(api_key="test-key", client=client)

    with pytest.raises(StructuredOutputError):
        openrouter.synthesize_cluster({"cluster_id": "abc", "articles": []})


def test_openrouter_client_retries_on_server_error():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(500, json={"error": {"message": "temporary"}})
        return httpx.Response(200, json=_rewrite_response())

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://test")
    openrouter = OpenRouterClient(api_key="test-key", client=client)

    result = openrouter.synthesize_cluster({"cluster_id": "abc", "articles": []})
    assert result.action == "rewrite"
    assert attempts["count"] == 2


def test_openrouter_client_raises_after_retry_exhausted():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "temporary"}})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://test")
    openrouter = OpenRouterClient(api_key="test-key", client=client)

    with pytest.raises(SynthesisError):
        openrouter.synthesize_cluster({"cluster_id": "abc", "articles": []})
