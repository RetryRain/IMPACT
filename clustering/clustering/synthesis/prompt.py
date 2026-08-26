from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from clustering.config import get_settings

CANONICAL_SCOPES = frozenset({"India", "Tamil Nadu", "World"})

CANONICAL_CATEGORIES = frozenset({
    "politics",
    "economy",
    "crime",
    "courts",
    "tech",
    "health",
    "environment",
    "sports",
    "culture",
})

RELEVANCE_SYSTEM_PROMPT = """You are TNDecaf, a neutral news intelligence editor.

Decide whether TNDecaf should publish a cluster of articles about the same real-world event. You receive article titles only.

CORE PRINCIPLE
TNDecaf publishes only genuine news events with material public-interest consequences—not everything in the news. Quality over volume. No engagement bait.

KEEP when the event has real consequences for people, institutions, markets, safety, law, or governance—in Tamil Nadu, India, or the world.

KEEP examples:
- Major policy, law, or court ruling
- Significant economic or market development
- Public health or safety event with wider concern
- Infrastructure, energy, or transport disruption
- Major international event with global consequences
- TN state government, institutions, or public services

DROP categories: gossip/entertainment; celebrity/personal incidents; pointless controversies; routine sports scores/highlights; ads/promos; opinion/editorial; listicles/lifestyle without news event; duplicate/non-news; isolated personal crime without wider concern; political noise without policy effect; sensational but low practical value; speculation without factual basis.

Don't keep for: shocking, controversial, emotional, violent, politically interesting, famous, trending, widely reported—without meaningful public relevance.

Don't prioritize clicks over usefulness.

DECISION ORDER
1. Genuine real-world event/development?
2. Meaningful consequences for people/business/government/economy?
3. Titles suggest enough to explain the event?
If any is NO → drop.

Output JSON only: action "keep" or "drop"; drop_reason one word when drop, null when keep."""

REWRITE_SYSTEM_PROMPT = """You are TNDecaf, a neutral news intelligence editor.

This cluster passed relevance review. Synthesize all supplied sources into one original, factual, source-grounded story. If sources lack enough reliable detail, return action="drop".

SYNTHESIS
- Read ALL sources before writing.
- One story covering every material distinct point from the cluster—not only the lead article's angle.
- Synthesize; don't copy or lightly paraphrase one article.
- Use only supplied-source facts. Never invent quotes, numbers, dates, motives, causes, context.
- Source disagreements: neutral phrasing ("Sources disagree..."); don't name outlets in headline/summary/body.
- No manufactured consensus; prefer verifiable facts; distinguish facts from allegations/claims.
- No outside/general knowledge.
- Don't infer TN relevance unless supported by sources.

STYLE
Neutral, factual, concise. Simple vocabulary. No sensationalism, clickbait, loaded language, editorializing. No favoring parties/governments/outlets. Don't exaggerate or hide disagreement. Explain what happened, why it matters, what's known.

SCOPE (assigned_scope is a hint)
Return scope exactly one of: India, Tamil Nadu, World — where the event primarily belongs:
- Tamil Nadu: TN geography, government, institutions, residents, local services
- India: national event
- World: international event

CATEGORY
Return exactly one primary topic slug. Scope already covers geography (World vs India vs Tamil Nadu)—do not use a geography as category.
- politics: elections, government, policy, diplomacy, foreign affairs
- economy: markets, trade, business, jobs, inflation
- crime: crime with wider public concern
- courts: court rulings, legal proceedings
- tech: science, technology, research
- health: public health, medicine, hospitals
- environment: climate, pollution, natural disasters
- sports: only major sporting events with public consequence (not routine scores)
- culture: arts, heritage, education with public impact

PRIORITY (1–100, importance within assigned scope—not article/outlet count)
- 80–100: major urgent event with wide consequences
- 60–79: significant, narrower or less urgent
- 40–59: legitimate public interest, moderate impact
- 20–39: notable but limited practical effect
- 1–19: barely passed relevance

Output JSON only: action "rewrite" or "drop"; when rewrite: scope, category, priority, title, summary, body; when drop: drop_reason one word, others null."""

CLASSIFY_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["keep", "drop"],
            "description": "Whether the cluster should proceed to rewrite",
        },
        "drop_reason": {
            "type": ["string", "null"],
            "description": "Required when action is drop; otherwise null",
        },
    },
    "required": ["action", "drop_reason"],
    "additionalProperties": False,
}

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
        "scope": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "string",
                    "enum": ["India", "Tamil Nadu", "World"],
                },
            ],
            "description": "Verified geographic scope when action is rewrite",
        },
        "category": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "string",
                    "enum": sorted(CANONICAL_CATEGORIES),
                },
            ],
            "description": "Primary news category when action is rewrite",
        },
        "priority": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                },
            ],
            "description": "Editorial priority 1-100 when action is rewrite",
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
    "required": [
        "action",
        "drop_reason",
        "scope",
        "category",
        "priority",
        "title",
        "summary",
        "body",
    ],
    "additionalProperties": False,
}


def _compact_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def normalize_scope(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped:
        return None
    lowered = stripped.lower().replace("_", " ")
    if lowered in {"tamil nadu", "tamilnadu"}:
        return "Tamil Nadu"
    if lowered == "india":
        return "India"
    if lowered == "world":
        return "World"
    return stripped


def normalize_category(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if not stripped:
        return None
    aliases = {
        "science": "tech",
        "science_and_tech": "tech",
        "sci_tech": "tech",
        "law": "courts",
        "legal": "courts",
        "world": "politics",
        "foreign": "politics",
        "international": "politics",
        "diplomacy": "politics",
        "foreign_affairs": "politics",
    }
    normalized = aliases.get(stripped, stripped)
    if normalized in CANONICAL_CATEGORIES:
        return normalized
    return stripped if stripped in CANONICAL_CATEGORIES else None


def _coerce_action(data: dict[str, Any], *, keep_value: str) -> None:
    if "action" in data:
        action = str(data["action"]).strip().lower()
        if action == "rewrite":
            data["action"] = keep_value
        elif action == "keep" and keep_value == "rewrite":
            data["action"] = "rewrite"
        else:
            data["action"] = action
        return

    publish = data.pop("publish", None)
    if publish is None:
        return
    if isinstance(publish, bool):
        data["action"] = keep_value if publish else "drop"
    elif isinstance(publish, str):
        data["action"] = (
            keep_value
            if publish.strip().lower() in {"true", "yes", "1"}
            else "drop"
        )


def coerce_classify_payload(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    _coerce_action(normalized, keep_value="keep")

    for alt_key, canonical_key in (("reason", "drop_reason"), ("dropReason", "drop_reason")):
        if alt_key in normalized and canonical_key not in normalized:
            normalized[canonical_key] = normalized.pop(alt_key)

    if normalized.get("action") == "keep":
        normalized["drop_reason"] = None

    return normalized


def coerce_synthesis_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Map common alternate LLM keys onto the canonical synthesis schema."""
    normalized = dict(data)
    _coerce_action(normalized, keep_value="rewrite")

    for alt_key, canonical_key in (
        ("reason", "drop_reason"),
        ("dropReason", "drop_reason"),
        ("headline", "title"),
        ("rewrite_title", "title"),
        ("rewrite_summary", "summary"),
        ("rewrite_body", "body"),
        ("article_body", "body"),
        ("priority_points", "priority"),
        ("priority_score", "priority"),
        ("primary_category", "category"),
        ("news_category", "category"),
    ):
        if alt_key in normalized and canonical_key not in normalized:
            normalized[canonical_key] = normalized.pop(alt_key)

    if "scope" in normalized:
        normalized["scope"] = normalize_scope(normalized.get("scope"))

    if "category" in normalized:
        normalized["category"] = normalize_category(normalized.get("category"))

    priority = normalized.get("priority")
    if priority == "" or priority is None:
        normalized["priority"] = None
    elif isinstance(priority, str) and priority.strip().isdigit():
        normalized["priority"] = int(priority.strip())

    if normalized.get("action") == "drop":
        normalized["title"] = None
        normalized["summary"] = None
        normalized["body"] = None
        normalized["scope"] = None
        normalized["category"] = None
        normalized["priority"] = None

    return normalized


def parse_classify_result(data: dict[str, Any]) -> ClassifyResult:
    return ClassifyResult.model_validate(coerce_classify_payload(data))


def parse_synthesis_result(data: dict[str, Any]) -> SynthesisResult:
    return SynthesisResult.model_validate(coerce_synthesis_payload(data))


class ClassifyResult(BaseModel):
    action: Literal["keep", "drop"]
    drop_reason: str | None = None

    @model_validator(mode="after")
    def validate_action_fields(self) -> ClassifyResult:
        if self.action == "keep":
            if self.drop_reason is not None and str(self.drop_reason).strip():
                raise ValueError("keep requires drop_reason to be null")
        elif self.action == "drop":
            if not (self.drop_reason or "").strip():
                raise ValueError("drop requires a non-empty drop_reason")
        return self


class SynthesisResult(BaseModel):
    action: Literal["rewrite", "drop"]
    drop_reason: str | None = None
    scope: Literal["India", "Tamil Nadu", "World"] | None = None
    category: str | None = None
    priority: int | None = Field(default=None, ge=1, le=100)
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
                    ("scope", self.scope),
                    ("category", self.category),
                    ("priority", self.priority),
                )
                if value is None or (
                    isinstance(value, str) and not value.strip()
                )
            ]
            if missing:
                raise ValueError(
                    f"rewrite requires non-empty fields: {', '.join(missing)}"
                )
            if self.scope not in CANONICAL_SCOPES:
                raise ValueError(
                    f"rewrite requires scope to be one of: "
                    f"{', '.join(sorted(CANONICAL_SCOPES))}"
                )
            if self.category not in CANONICAL_CATEGORIES:
                raise ValueError(
                    f"rewrite requires category to be one of: "
                    f"{', '.join(sorted(CANONICAL_CATEGORIES))}"
                )
        elif self.action == "drop":
            if not (self.drop_reason or "").strip():
                raise ValueError("drop requires a non-empty drop_reason")
            if (
                self.scope is not None
                or self.category is not None
                or self.priority is not None
            ):
                raise ValueError(
                    "drop requires scope, category, and priority to be null"
                )
        return self


def compact_classify_payload(payload: dict[str, Any]) -> dict[str, Any]:
    titles: list[str] = []
    for article in payload.get("articles", []):
        title = article.get("title")
        if isinstance(title, str) and title.strip():
            titles.append(title.strip())
    return {"titles": titles}


def compact_rewrite_payload(payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    limit = settings.synthesis_body_char_limit
    articles = []
    for article in payload.get("articles", []):
        body = article.get("body") or ""
        if limit > 0 and len(body) > limit:
            body = body[:limit]
        articles.append(
            {
                "title": article.get("title"),
                "summary": article.get("summary"),
                "body": body,
            }
        )
    return {
        "assigned_scope": payload.get("scope"),
        "articles": articles,
    }


def build_classify_user_message(payload: dict[str, Any]) -> str:
    compact = compact_classify_payload(payload)
    return (
        "Review these article titles for public-interest news quality. "
        "Respond with JSON only.\n"
        f"{_compact_json(compact)}"
    )


def build_rewrite_user_message(payload: dict[str, Any]) -> str:
    compact = compact_rewrite_payload(payload)
    return (
        "Synthesize this cluster. Verify assigned_scope and respond with JSON only.\n"
        f"{_compact_json(compact)}"
    )
