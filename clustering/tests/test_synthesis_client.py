import json

import httpx
import pytest

from clustering.synthesis.client import get_synthesis_client
from clustering.synthesis.deepseek_client import DeepSeekClient
from clustering.synthesis.prompt import RELEVANCE_SYSTEM_PROMPT, REWRITE_SYSTEM_PROMPT


def test_get_synthesis_client_deepseek_requires_api_key(monkeypatch):
    monkeypatch.setenv("SYNTHESIS_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from clustering.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(SystemExit, match="DEEPSEEK_API_KEY"):
        get_synthesis_client()


def test_get_synthesis_client_openrouter_requires_api_key(monkeypatch):
    monkeypatch.setenv("SYNTHESIS_PROVIDER", "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from clustering.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(SystemExit, match="OPENROUTER_API_KEY"):
        get_synthesis_client()


def test_deepseek_client_uses_json_object_format():
    seen_prompts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["model"] == "deepseek-chat"
        assert body["response_format"] == {"type": "json_object"}
        assert request.headers["Authorization"] == "Bearer test-deepseek-key"
        seen_prompts.append(body["messages"][0]["content"])
        if seen_prompts[-1] == RELEVANCE_SYSTEM_PROMPT:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"action": "keep", "drop_reason": None}
                                )
                            }
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
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
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://test")
    deepseek = DeepSeekClient(
        api_key="test-deepseek-key",
        base_url="http://test",
        model="deepseek-chat",
        client=client,
    )
    classify_result = deepseek.classify_cluster(
        {"articles": [{"title": "Policy update"}]}
    )
    assert classify_result.action == "keep"

    result = deepseek.synthesize_cluster({"cluster_id": "abc", "articles": []})
    assert result.action == "rewrite"
    assert result.title == "Rewritten"
    assert seen_prompts == [RELEVANCE_SYSTEM_PROMPT, REWRITE_SYSTEM_PROMPT]
