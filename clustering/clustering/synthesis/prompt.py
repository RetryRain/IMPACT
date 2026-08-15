from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, model_validator

from clustering.config import get_settings

SYSTEM_PROMPT = """You are a neutral news editor synthesizing clustered articles about the same real-world event.

Rules:
1. Decide whether this cluster is worth publishing.
2. DROP irrelevant clusters: celebrity gossip, sports scores/highlights, ads, opinion columns, listicles, or articles that are not about a single real-world news event.
3. If you KEEP the cluster, write one unbiased story using ALL sources in the payload.
4. Do not invent facts not supported by the sources. If sources disagree, note the disagreement neutrally.
5. Avoid loaded language, editorializing, and outlet-specific framing.
6. Output JSON only matching the provided schema. Do not use tools or request permissions.
"""

SYNTHESIS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["rewrite", "drop"],
            "description": "Whether to publish a rewritten story or drop the cluster",
        },
        "drop_reason": {
            "type": ["string", "null"],
            "description": "Required when action is drop; otherwise null",
        },
        "title": {
            "type": ["string", "null"],
            "description": "Rewritten headline when action is rewrite",
        },
        "summary": {
            "type": ["string", "null"],
            "description": "Rewritten summary when action is rewrite",
        },
        "body": {
            "type": ["string", "null"],
            "description": "Rewritten article body when action is rewrite",
        },
    },
    "required": ["action", "drop_reason", "title", "summary", "body"],
    "additionalProperties": False,
}


class SynthesisResult(BaseModel):
    action: Literal["rewrite", "drop"]
    drop_reason: str | None = None
    title: str | None = None
    summary: str | None = None
    body: str | None = None

    @model_validator(mode="after")
    def validate_action_fields(self) -> SynthesisResult:
        if self.action == "rewrite":
            missing = [
                field
                for field, value in (
                    ("title", self.title),
                    ("summary", self.summary),
                    ("body", self.body),
                )
                if not value or not str(value).strip()
            ]
            if missing:
                raise ValueError(
                    f"rewrite requires non-empty fields: {', '.join(missing)}"
                )
        elif self.action == "drop" and not (self.drop_reason or "").strip():
            raise ValueError("drop requires a non-empty drop_reason")
        return self


def compact_cluster_payload(payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    limit = settings.synthesis_body_char_limit
    articles = []
    for article in payload.get("articles", []):
        body = article.get("body") or ""
        if limit > 0 and len(body) > limit:
            body = body[:limit]
        articles.append(
            {
                "source": article.get("source"),
                "title": article.get("title"),
                "url": article.get("url"),
                "summary": article.get("summary"),
                "body": body,
                "published_at": article.get("published_at"),
            }
        )
    return {
        "cluster_id": payload.get("cluster_id"),
        "scope": payload.get("scope"),
        "article_count": payload.get("article_count"),
        "articles": articles,
    }


def build_user_message(payload: dict[str, Any]) -> str:
    compact = compact_cluster_payload(payload)
    return (
        "Review this news cluster and respond with JSON only.\n\n"
        f"{json.dumps(compact, indent=2, ensure_ascii=False)}"
    )
