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
    normalize_scope,
    parse_synthesis_result,
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
    assert compact["assigned_scope"] == "India"
    assert "article_count" not in compact
    assert "scope" not in compact


def test_synthesis_result_requires_rewrite_fields():
    with pytest.raises(ValidationError):
        SynthesisResult(
            action="rewrite",
            drop_reason=None,
            scope=None,
            priority=None,
            title="Only title",
            summary=None,
            body=None,
        )


def test_synthesis_result_requires_drop_reason():
    with pytest.raises(ValidationError):
        SynthesisResult(
            action="drop",
            drop_reason=None,
            scope=None,
            priority=None,
            title=None,
            summary=None,
            body=None,
        )


def test_synthesis_result_drop_rejects_scope_and_priority():
    with pytest.raises(ValidationError):
        SynthesisResult(
            action="drop",
            drop_reason="Sports",
            scope="India",
            priority=50,
            title=None,
            summary=None,
            body=None,
        )


def test_synthesis_result_rewrite_requires_scope_and_priority():
    result = SynthesisResult(
        action="rewrite",
        drop_reason=None,
        scope="Tamil Nadu",
        priority=75,
        title="Headline",
        summary="Summary",
        body="Body",
    )
    assert result.scope == "Tamil Nadu"
    assert result.priority == 75


def test_normalize_scope_aliases():
    assert normalize_scope("TamilNadu") == "Tamil Nadu"
    assert normalize_scope("tamil nadu") == "Tamil Nadu"
    assert normalize_scope("India") == "India"
    assert normalize_scope("World") == "World"


def test_coerce_priority_points_alias():
    result = parse_synthesis_result(
        {
            "action": "rewrite",
            "drop_reason": None,
            "scope": "India",
            "priority_points": 55,
            "title": "Headline",
            "summary": "Summary",
            "body": "Body",
        }
    )
    assert result.priority == 55


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
    assert "assigned_scope" in message
    assert "Verify assigned_scope" in message


def test_coerce_drop_clears_scope_and_priority():
    result = parse_synthesis_result(
        {
            "action": "drop",
            "drop_reason": "irrelevant",
            "scope": "India",
            "priority": 50,
            "title": "ignored",
            "summary": "ignored",
            "body": "ignored",
        }
    )
    assert result.action == "drop"
    assert result.scope is None
    assert result.priority is None
    assert result.title is None


def test_extract_json_from_reasoning_text():
    from clustering.synthesis.openrouter_client import _extract_json_object

    text = (
        "We should DROP.\n\n"
        "Thus output:\n\n"
        "{\n"
        '  "action": "drop",\n'
        '  "drop_reason": "irrelevant",\n'
        '  "scope": null,\n'
        '  "priority": null\n'
        "}\n"
    )
    data = _extract_json_object(text)
    assert data["action"] == "drop"
    assert data["drop_reason"] == "irrelevant"


def test_message_text_reads_reasoning_field():
    from clustering.synthesis.openrouter_client import _message_text

    message = {
        "role": "assistant",
        "content": None,
        "reasoning": '{"action": "drop", "drop_reason": "irrelevant"}',
    }
    assert _message_text(message) == message["reasoning"]
    result = parse_synthesis_result(
        {
            "publish": False,
            "reason": "Sports highlight",
        }
    )
    assert result.action == "drop"
    assert result.drop_reason == "Sports highlight"


def test_coerce_publish_true_maps_to_rewrite():
    result = parse_synthesis_result(
        {
            "publish": True,
            "scope": "TamilNadu",
            "priority": 60,
            "title": "Headline",
            "summary": "Summary",
            "body": "Body",
        }
    )
    assert result.action == "rewrite"
    assert result.title == "Headline"
    assert result.scope == "Tamil Nadu"


def _rewrite_response() -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": "rewrite",
                            "drop_reason": None,
                            "scope": "India",
                            "priority": 65,
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
    assert result.scope == "India"
    assert result.priority == 65


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
                                        "scope": "World",
                                        "priority": 45,
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
    assert result.scope == "World"
    assert result.priority == 45


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


def test_openrouter_client_coerces_publish_false_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "publish": False,
                                    "reason": "Not a single news event",
                                }
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
    assert result.action == "drop"
    assert result.drop_reason == "Not a single news event"
