from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from clustering.config import get_settings
from clustering.timezone_util import IST


def _resolve_log_path(configured: str) -> Path | None:
    stripped = configured.strip()
    if not stripped:
        return None
    raw = Path(stripped)
    if raw.is_absolute():
        return raw
    return Path.cwd() / raw


def _default_log_path() -> Path:
    return Path(__file__).resolve().parents[2] / "logs" / "synthesis.jsonl"


def provider_model() -> tuple[str, str]:
    settings = get_settings()
    provider = settings.synthesis_provider.strip().lower()
    if provider == "openrouter":
        return provider, settings.openrouter_model
    return provider, settings.deepseek_model


class SynthesisRunLog:
    """Append-only JSONL log for synthesis runs (thread-safe)."""

    def __init__(self, path: Path | None = None) -> None:
        if path is not None:
            self._path = path
        else:
            configured = get_settings().synthesis_log_path
            resolved = _resolve_log_path(configured)
            self._path = resolved if resolved is not None else _default_log_path()
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def write_entry(self, entry: dict[str, Any]) -> None:
        line = json.dumps(entry, ensure_ascii=False, default=str)
        with self._lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def log_cluster(self, **fields: Any) -> None:
        provider, model = provider_model()
        entry: dict[str, Any] = {
            "type": "cluster",
            "timestamp": datetime.now(IST).isoformat(),
            "provider": provider,
            "model": model,
            **fields,
        }
        self.write_entry(entry)

    def log_summary(self, stats: dict[str, Any], **fields: Any) -> None:
        provider, model = provider_model()
        entry: dict[str, Any] = {
            "type": "summary",
            "timestamp": datetime.now(IST).isoformat(),
            "provider": provider,
            "model": model,
            "stats": stats,
            **fields,
        }
        self.write_entry(entry)
