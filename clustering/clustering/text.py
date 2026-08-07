from __future__ import annotations

import hashlib
import re

from clustering.config import get_settings

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def build_embedding_text(
    title: str | None,
    summary: str | None,
    body: str | None,
    *,
    body_char_limit: int | None = None,
) -> str:
    settings = get_settings()
    limit = body_char_limit if body_char_limit is not None else settings.body_char_limit

    parts: list[str] = []
    if title:
        parts.append(normalize_whitespace(title))
    if summary:
        parts.append(normalize_whitespace(summary))
    if body:
        normalized_body = normalize_whitespace(body)
        if limit > 0:
            normalized_body = normalized_body[:limit]
        parts.append(normalized_body)

    if not parts and title:
        parts.append(normalize_whitespace(title))

    return "\n".join(parts)


def hash_embedding_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
