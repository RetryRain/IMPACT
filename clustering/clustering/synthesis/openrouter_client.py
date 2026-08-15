from __future__ import annotations

import json
import time
from typing import Any

import httpx
from pydantic import ValidationError

from clustering.config import get_settings
from clustering.synthesis.prompt import (
    SYNTHESIS_JSON_SCHEMA,
    SYSTEM_PROMPT,
    SynthesisResult,
    build_user_message,
)

def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


class SynthesisError(RuntimeError):
    pass


class StructuredOutputError(SynthesisError):
    pass


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
        self.api_key = api_key if api_key is not None else settings.openrouter_api_key
        self.base_url = (base_url or settings.openrouter_base_url).rstrip("/")
        self.model = model or settings.openrouter_model
        self.timeout_seconds = timeout_seconds or settings.synthesis_timeout_seconds
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/impact-clustering",
                "X-Title": "impact-clustering",
            },
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> OpenRouterClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def synthesize_cluster(self, payload: dict[str, Any]) -> SynthesisResult:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_message(payload)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "synthesis_result",
                    "strict": True,
                    "schema": SYNTHESIS_JSON_SCHEMA,
                },
            },
        }
        response = self._post_with_retry("/chat/completions", body)
        return self._parse_response(response)

    def _post_with_retry(self, path: str, body: dict[str, Any]) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = self._client.post(path, json=body)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                raise SynthesisError(f"OpenRouter request failed: {exc}") from exc

            if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                time.sleep(1.0)
                continue

            self._raise_for_status(response)
            return response

        if last_error is not None:
            raise SynthesisError(f"OpenRouter request failed: {last_error}") from last_error
        raise SynthesisError("OpenRouter request failed after retries")

    def _parse_response(self, response: httpx.Response) -> SynthesisResult:
        try:
            payload = response.json()
        except ValueError as exc:
            raise StructuredOutputError("OpenRouter returned non-JSON response") from exc

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise StructuredOutputError(
                f"OpenRouter response missing choices: {payload}"
            )

        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise StructuredOutputError(
                f"OpenRouter response missing message content: {payload}"
            )

        return self._parse_structured_content(content)

    def _parse_structured_content(self, content: str) -> SynthesisResult:
        text = _strip_markdown_fences(content)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise StructuredOutputError(
                f"OpenRouter returned invalid JSON: {exc}"
            ) from exc

        try:
            return SynthesisResult.model_validate(data)
        except ValidationError as exc:
            raise StructuredOutputError(
                f"OpenRouter JSON failed validation: {exc}"
            ) from exc

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        detail = response.text
        try:
            payload = response.json()
            if isinstance(payload, dict):
                error = payload.get("error")
                if isinstance(error, dict):
                    detail = error.get("message") or detail
                else:
                    detail = payload.get("message") or detail
        except ValueError:
            pass
        raise SynthesisError(
            f"OpenRouter request failed ({response.status_code}): {detail}"
        )
