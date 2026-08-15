from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx
from pydantic import ValidationError

from clustering.synthesis.prompt import (
    SYSTEM_PROMPT,
    SynthesisResult,
    build_user_message,
    parse_synthesis_result,
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


def _message_text(message: dict[str, Any]) -> str | None:
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()

    reasoning = message.get("reasoning")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning.strip()

    details = message.get("reasoning_details")
    if isinstance(details, list):
        parts: list[str] = []
        for item in details:
            if isinstance(item, dict) and item.get("type") == "reasoning.text":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        if parts:
            return "\n".join(parts)

    return None


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = _strip_markdown_fences(text)
    if not stripped:
        raise ValueError("empty text")

    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    for start in range(len(stripped) - 1, -1, -1):
        if stripped[start] != "{":
            continue
        candidate = stripped[start:]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue

    raise ValueError("no JSON object found")


class SynthesisError(RuntimeError):
    pass


class StructuredOutputError(SynthesisError):
    pass


class ChatCompletionsClient:
    def __init__(
        self,
        *,
        provider_name: str,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        extra_headers: dict[str, str] | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._owns_client = client is None
        headers = {"Authorization": f"Bearer {api_key}"}
        if extra_headers:
            headers.update(extra_headers)
        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            headers=headers,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> ChatCompletionsClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def synthesize_cluster(
        self,
        payload: dict[str, Any],
        *,
        response_format: dict[str, Any],
    ) -> SynthesisResult:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_message(payload)},
            ],
            "response_format": response_format,
        }
        last_error: StructuredOutputError | None = None
        for attempt in range(2):
            try:
                response = self._post_with_retry("/chat/completions", body)
                return self._parse_response(response)
            except StructuredOutputError as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise SynthesisError("synthesis failed after retries")

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
                raise SynthesisError(
                    f"{self.provider_name} request failed: {exc}"
                ) from exc

            if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                time.sleep(1.0)
                continue

            self._raise_for_status(response)
            return response

        if last_error is not None:
            raise SynthesisError(
                f"{self.provider_name} request failed: {last_error}"
            ) from last_error
        raise SynthesisError(f"{self.provider_name} request failed after retries")

    def _parse_response(self, response: httpx.Response) -> SynthesisResult:
        try:
            payload = response.json()
        except ValueError as exc:
            raise StructuredOutputError(
                f"{self.provider_name} returned non-JSON response"
            ) from exc

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise StructuredOutputError(
                f"{self.provider_name} response missing choices: {payload}"
            )

        choice = choices[0]
        message = choice.get("message", {})
        if not isinstance(message, dict):
            raise StructuredOutputError(
                f"{self.provider_name} response missing message: {payload}"
            )

        text = _message_text(message)
        if not text:
            raise StructuredOutputError(
                f"{self.provider_name} response missing message content: {payload}"
            )

        return self._parse_structured_content(text)

    def _parse_structured_content(self, content: str) -> SynthesisResult:
        try:
            data = _extract_json_object(content)
        except ValueError as exc:
            raise StructuredOutputError(
                f"{self.provider_name} returned invalid JSON: {exc}"
            ) from exc

        try:
            return parse_synthesis_result(data)
        except ValidationError as exc:
            raise StructuredOutputError(
                f"{self.provider_name} JSON failed validation: {exc}"
            ) from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
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
            f"{self.provider_name} request failed ({response.status_code}): {detail}"
        )
