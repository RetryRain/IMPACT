from __future__ import annotations

from typing import Any, Protocol

from clustering.config import get_settings
from clustering.synthesis.deepseek_client import DeepSeekClient
from clustering.synthesis.openrouter_client import OpenRouterClient
from clustering.synthesis.prompt import ClassifyResult, SynthesisResult


class SynthesisClient(Protocol):
    def classify_cluster(self, payload: dict[str, Any]) -> ClassifyResult: ...

    def synthesize_cluster(self, payload: dict[str, Any]) -> SynthesisResult: ...

    def close(self) -> None: ...


def get_synthesis_client() -> SynthesisClient:
    settings = get_settings()
    provider = settings.synthesis_provider.strip().lower()

    if provider == "deepseek":
        if not settings.deepseek_api_key:
            raise SystemExit(
                "DEEPSEEK_API_KEY is required when SYNTHESIS_PROVIDER=deepseek. "
                "Set it in clustering/.env and retry."
            )
        return DeepSeekClient()

    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise SystemExit(
                "OPENROUTER_API_KEY is required when SYNTHESIS_PROVIDER=openrouter. "
                "Set it in clustering/.env and retry."
            )
        return OpenRouterClient()

    raise SystemExit(
        f"Unknown SYNTHESIS_PROVIDER={settings.synthesis_provider!r}. "
        "Use deepseek or openrouter."
    )
