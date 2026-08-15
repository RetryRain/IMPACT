from __future__ import annotations

from typing import Any

import httpx

from clustering.config import get_settings
from clustering.synthesis.llm_client import (
    ChatCompletionsClient,
    SynthesisError,
    StructuredOutputError,
    _extract_json_object,
    _message_text,
)
from clustering.synthesis.prompt import SYNTHESIS_JSON_SCHEMA, SynthesisResult

# Re-export for tests and backward compatibility.
__all__ = [
    "OpenRouterClient",
    "SynthesisError",
    "StructuredOutputError",
    "_extract_json_object",
    "_message_text",
]

_OPENROUTER_JSON_SCHEMA_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "synthesis_result",
        "strict": True,
        "schema": SYNTHESIS_JSON_SCHEMA,
    },
}


class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        settings = get_settings()
        self._inner = ChatCompletionsClient(
            provider_name="OpenRouter",
            api_key=api_key if api_key is not None else settings.openrouter_api_key,
            base_url=(base_url or settings.openrouter_base_url),
            model=model or settings.openrouter_model,
            timeout_seconds=timeout_seconds or settings.synthesis_timeout_seconds,
            extra_headers={
                "HTTP-Referer": "https://github.com/impact-clustering",
                "X-Title": "impact-clustering",
            },
            client=client,
        )

    def close(self) -> None:
        self._inner.close()

    def __enter__(self) -> OpenRouterClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def synthesize_cluster(self, payload: dict[str, Any]) -> SynthesisResult:
        return self._inner.synthesize_cluster(
            payload,
            response_format=_OPENROUTER_JSON_SCHEMA_RESPONSE_FORMAT,
        )
