from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from clustering.config import get_settings
from clustering.timezone_util import IST


def _resolve_report_path(configured: str) -> Path:
    stripped = configured.strip()
    if not stripped:
        return _default_report_path()
    raw = Path(stripped)
    if raw.is_absolute():
        return raw
    return Path.cwd() / raw


def _default_report_path() -> Path:
    return Path(__file__).resolve().parents[2] / "logs" / "synthesis_reports.log"


def provider_model() -> tuple[str, str]:
    settings = get_settings()
    provider = settings.synthesis_provider.strip().lower()
    if provider == "openrouter":
        return provider, settings.openrouter_model
    return provider, settings.deepseek_model


def _scope_key(fields: dict[str, Any]) -> str:
    scope = fields.get("scope") or fields.get("assigned_scope")
    if isinstance(scope, str) and scope.strip():
        return scope.strip()
    return "unknown"


def format_synthesis_report(
    *,
    stats: dict[str, Any],
    scope_stats: dict[str, dict[str, int]],
    duration_ms: int,
    concurrency: int,
    provider: str,
    model: str,
    limit: int | None = None,
) -> str:
    examined = int(stats.get("examined", 0))
    rewritten = int(stats.get("rewritten", 0))
    dropped = int(stats.get("dropped", 0))
    failed = int(stats.get("failed", 0))
    skipped = int(stats.get("skipped_existing", 0))

    elapsed_s = duration_ms / 1000
    clusters_per_sec = examined / elapsed_s if elapsed_s > 0 else 0.0
    llm_calls = rewritten + dropped + failed
    drop_rate = (dropped / llm_calls * 100) if llm_calls else 0.0

    timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %Z")
    limit_label = str(limit) if limit is not None else "none"

    scope_lines: list[str] = []
    for scope in sorted(scope_stats):
        bucket = scope_stats[scope]
        scope_lines.append(
            "  "
            + f"[{scope}] rewritten={bucket.get('rewritten', 0)} "
            + f"dropped={bucket.get('dropped', 0)} "
            + f"failed={bucket.get('failed', 0)} "
            + f"skipped={bucket.get('skipped_existing', 0)}"
        )
    scope_block = "\n".join(scope_lines) if scope_lines else "  (no scope stats)"

    return (
        "\n"
        + "=" * 60
        + "\n"
        + f"Timestamp             : {timestamp}\n"
        + f"Provider              : {provider}\n"
        + f"Model                 : {model}\n"
        + f"Cluster limit         : {limit_label}\n"
        + f"Clusters examined     : {examined}\n"
        + f"Rewritten             : {rewritten}\n"
        + f"Dropped               : {dropped}\n"
        + f"Skipped (existing)    : {skipped}\n"
        + f"Failed                : {failed}\n"
        + f"Drop rate             : {drop_rate:.2f}%\n"
        + f"Elapsed time          : {elapsed_s:.2f} s\n"
        + f"Clusters/sec          : {clusters_per_sec:.2f}\n"
        + f"Concurrency           : {concurrency}\n"
        + "Scope summaries       :\n"
        + scope_block
        + "\n"
        + "=" * 60
    )


class SynthesisRunLog:
    """Append-only human-readable synthesis log (thread-safe)."""

    def __init__(self, path: Path | None = None) -> None:
        if path is not None:
            self._path = path
        else:
            self._path = _resolve_report_path(get_settings().synthesis_report_path)
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._scope_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    @property
    def path(self) -> Path:
        return self._path

    def _append_report(self, report: str) -> None:
        with self._lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(report + "\n")

    def _record_scope(self, fields: dict[str, Any]) -> None:
        outcome = str(fields.get("outcome", "unknown"))
        scope = _scope_key(fields)
        with self._lock:
            self._scope_stats[scope][outcome] += 1

    def log_cluster(self, **fields: Any) -> None:
        self._record_scope(fields)

    def log_summary(
        self,
        stats: dict[str, Any],
        *,
        limit: int | None = None,
        **fields: Any,
    ) -> Path:
        duration_ms = int(fields.get("duration_ms", 0))
        concurrency = int(fields.get("concurrency", 1))
        provider, model = provider_model()

        with self._lock:
            scope_stats = {
                scope: dict(outcomes)
                for scope, outcomes in self._scope_stats.items()
            }

        report = format_synthesis_report(
            stats=stats,
            scope_stats=scope_stats,
            duration_ms=duration_ms,
            concurrency=concurrency,
            provider=provider,
            model=model,
            limit=limit,
        )
        self._append_report(report)
        return self._path
