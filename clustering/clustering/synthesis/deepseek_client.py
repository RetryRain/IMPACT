from __future__ import annotations

from typing import Any

import httpx

from clustering.config import get_settings
from clustering.synthesis.llm_client import ChatCompletionsClient
from clustering.synthesis.prompt import ClassifyResult, SynthesisResult

_DEEPSEEK_JSON_OBJECT_RESPONSE_FORMAT: dict[str, Any] = {"type": "json_object"}


class DeepSeekClient:
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
            provider_name="DeepSeek",
            api_key=api_key if api_key is not None else settings.deepseek_api_key,
            base_url=(base_url or settings.deepseek_base_url),
            model=model or settings.deepseek_model,
            timeout_seconds=timeout_seconds or settings.synthesis_timeout_seconds,
            client=client,
        )

    def close(self) -> None:
        self._inner.close()

    def __enter__(self) -> DeepSeekClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def classify_cluster(self, payload: dict[str, Any]) -> ClassifyResult:
        return self._inner.classify_cluster(
            payload,
            response_format=_DEEPSEEK_JSON_OBJECT_RESPONSE_FORMAT,
        )

    def synthesize_cluster(self, payload: dict[str, Any]) -> SynthesisResult:
        return self._inner.synthesize_cluster(
            payload,
            response_format=_DEEPSEEK_JSON_OBJECT_RESPONSE_FORMAT,
        )
