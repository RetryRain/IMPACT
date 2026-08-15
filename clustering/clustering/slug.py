from __future__ import annotations

import re
import uuid


def slugify_title(title: str, max_length: int = 80) -> str:
    text = title.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    if not text:
        return "story"
    if len(text) > max_length:
        text = text[:max_length].rstrip("-")
    return text or "story"


def make_story_slug(title: str, story_id: uuid.UUID) -> str:
    base = slugify_title(title)
    suffix = str(story_id).replace("-", "")[:6]
    return f"{base}-{suffix}"
