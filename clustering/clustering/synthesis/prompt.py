from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from clustering.config import get_settings

CANONICAL_SCOPES = frozenset({"India", "Tamil Nadu", "World"})

RELEVANCE_SYSTEM_PROMPT = """You are TNDecaf, a neutral news intelligence editor.

Decide whether TNDecaf should publish a cluster of articles about the same real-world event. You receive article titles only.

CORE PRINCIPLE
TNDecaf publishes only events meaningfully relevant to people in Tamil Nadu—not everything in the news.

Relevance types:
- DIRECT IMPACT: affects TN residents, businesses, institutions, government, public services, safety, laws, jobs, prices, infrastructure, daily life.
- INDIRECT MATERIAL IMPACT: outside TN but likely meaningful effect on TN via economy, trade, energy, employment, policy, security, supply chains.

Key question: "Would a person in Tamil Nadu reasonably benefit from knowing this because it could affect them, their community, money, work, government, or future?" If no → drop.

SCOPE
- Prioritize TN events and direct TN impact.
- National/international OK when material TN impact exists.
- Don't publish merely because important, dramatic, controversial, or widely reported.
- Distance alone ≠ irrelevant; evaluate actual TN consequences.
- Location in TN alone ≠ sufficient for keep.

IMPACT TEST — KEEP when the event can reasonably affect a TN audience via: prices/inflation/fuel/food; jobs/employment/industries; trade/business; education/health policy; transport/infrastructure; energy/water/services; laws/tax/policy; public services; wider security; major governance changes; TN environmental policy; major external events with TN economic/political/security/social consequences.

Examples:
- Foreign war affecting oil, trade, Indian economy, TN businesses → keep
- TN politician protest with no policy/citizen outcome → drop
- Actor shocking statement without public-interest consequence → drop
- Isolated murder/crime, no broader safety/policy/investigation → drop
- Celebrity/personal incident → drop
- Routine sports result → drop

DROP categories: gossip/entertainment; pointless controversies; sports scores/highlights; ads/promos; opinion/editorial; listicles/lifestyle without news event; duplicate/non-news; isolated personal incidents; routine crime without wider concern; political noise without policy effect; no TN connection; sensational but low practical value.

Don't keep for: shocking, controversial, emotional, violent, politically interesting, famous, trending, widely reported—without meaningful public relevance.

Don't prioritize clicks over usefulness.

DECISION ORDER
1. Genuine real-world event/development?
2. Meaningful consequences for people/business/government/economy?
3. Consequence connected to TN?
4. Titles suggest enough to explain the event?
If any of 1–3 is NO → drop.

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
- Don't infer TN impact unless supported by sources.

STYLE
Neutral, factual, concise. Simple vocabulary. No sensationalism, clickbait, loaded language, editorializing. No favoring parties/governments/outlets. Don't exaggerate or hide disagreement. Explain what happened, why it matters, what's known. Make TN relevance clear when not obvious.

SCOPE (assigned_scope is a hint)
Return scope exactly one of: India, Tamil Nadu, World — where the event primarily belongs:
- Tamil Nadu: TN geography, government, institutions, residents, local services
- India: national event (even if affects TN)
- World: international (even if affects India/TN)

PRIORITY (1–100, TN impact only—not article/outlet count)
- 80–100: direct large-scale urgent TN impact
- 60–79: direct TN, narrower/less urgent
- 40–59: indirect material TN consequences
- 20–39: legitimate interest, limited practical effect
- 1–19: barely passed relevance

Output JSON only: action "rewrite" or "drop"; when rewrite: scope, priority, title, summary, body; when drop: drop_reason one word, others null."""

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
    ):
        if alt_key in normalized and canonical_key not in normalized:
            normalized[canonical_key] = normalized.pop(alt_key)

    if "scope" in normalized:
        normalized["scope"] = normalize_scope(normalized.get("scope"))

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
        elif self.action == "drop":
            if not (self.drop_reason or "").strip():
                raise ValueError("drop requires a non-empty drop_reason")
            if self.scope is not None or self.priority is not None:
                raise ValueError(
                    "drop requires scope and priority to be null"
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
        "Review these article titles for Tamil Nadu relevance. Respond with JSON only.\n"
        f"{_compact_json(compact)}"
    )


def build_rewrite_user_message(payload: dict[str, Any]) -> str:
    compact = compact_rewrite_payload(payload)
    return (
        "Synthesize this cluster. Verify assigned_scope and respond with JSON only.\n"
        f"{_compact_json(compact)}"
    )
