from __future__ import annotations

import json
import threading
from collections import defaultdict
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


def _default_report_path(jsonl_path: Path) -> Path:
    return jsonl_path.parent / "synthesis_reports.log"


def _resolve_report_path(configured_jsonl: str) -> Path:
    resolved = _resolve_log_path(configured_jsonl)
    jsonl_path = resolved if resolved is not None else _default_log_path()
    settings = get_settings()
    configured_report = settings.synthesis_report_path.strip()
    if configured_report:
        report = Path(configured_report)
        if report.is_absolute():
            return report
        return Path.cwd() / report
    return _default_report_path(jsonl_path)


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
    jsonl_path: Path,
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
        + f"JSONL log             : {jsonl_path}\n"
        + "Scope summaries       :\n"
        + scope_block
        + "\n"
        + "=" * 60
    )


def append_synthesis_report(
    *,
    stats: dict[str, Any],
    scope_stats: dict[str, dict[str, int]],
    duration_ms: int,
    concurrency: int,
    jsonl_path: Path,
    limit: int | None = None,
    report_path: Path | None = None,
) -> Path:
    provider, model = provider_model()
    destination = report_path or _resolve_report_path(
        get_settings().synthesis_log_path
    )
    destination.parent.mkdir(parents=True, exist_ok=True)

    report = format_synthesis_report(
        stats=stats,
        scope_stats=scope_stats,
        duration_ms=duration_ms,
        concurrency=concurrency,
        provider=provider,
        model=model,
        jsonl_path=jsonl_path,
        limit=limit,
    )

    with destination.open("a", encoding="utf-8") as handle:
        handle.write(report + "\n")

    stats_path = destination.parent / "synthesis_stats.jsonl"
    record = {
        "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %Z"),
        "provider": provider,
        "model": model,
        "limit": limit,
        "clusters_examined": int(stats.get("examined", 0)),
        "rewritten": int(stats.get("rewritten", 0)),
        "dropped": int(stats.get("dropped", 0)),
        "skipped_existing": int(stats.get("skipped_existing", 0)),
        "failed": int(stats.get("failed", 0)),
        "drop_rate": round(
            (
                int(stats.get("dropped", 0))
                / max(int(stats.get("rewritten", 0)) + int(stats.get("dropped", 0)) + int(stats.get("failed", 0)), 1)
            )
            * 100,
            2,
        ),
        "elapsed_seconds": round(duration_ms / 1000, 2),
        "concurrency": concurrency,
        "jsonl_log": str(jsonl_path),
        "scope_stats": scope_stats,
    }
    with stats_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    return destination


class SynthesisRunLog:
    """Append-only JSONL log for synthesis runs (thread-safe)."""

    def __init__(
        self,
        path: Path | None = None,
        report_path: Path | None = None,
    ) -> None:
        if path is not None:
            self._path = path
        else:
            configured = get_settings().synthesis_log_path
            resolved = _resolve_log_path(configured)
            self._path = resolved if resolved is not None else _default_log_path()
        self._report_path_override = report_path
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._scope_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    @property
    def path(self) -> Path:
        return self._path

    @property
    def report_path(self) -> Path:
        if self._report_path_override is not None:
            return self._report_path_override
        return _resolve_report_path(get_settings().synthesis_log_path)

    def write_entry(self, entry: dict[str, Any]) -> None:
        line = json.dumps(entry, ensure_ascii=False, default=str)
        with self._lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def _record_scope(self, fields: dict[str, Any]) -> None:
        outcome = str(fields.get("outcome", "unknown"))
        scope = _scope_key(fields)
        with self._lock:
            self._scope_stats[scope][outcome] += 1

    def log_cluster(self, **fields: Any) -> None:
        provider, model = provider_model()
        entry: dict[str, Any] = {
            "type": "cluster",
            "timestamp": datetime.now(IST).isoformat(),
            "provider": provider,
            "model": model,
            **fields,
        }
        self._record_scope(fields)
        self.write_entry(entry)

    def log_summary(
        self,
        stats: dict[str, Any],
        *,
        limit: int | None = None,
        **fields: Any,
    ) -> Path:
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

        duration_ms = int(fields.get("duration_ms", 0))
        concurrency = int(fields.get("concurrency", 1))
        with self._lock:
            scope_stats = {
                scope: dict(outcomes)
                for scope, outcomes in self._scope_stats.items()
            }

        return append_synthesis_report(
            stats=stats,
            scope_stats=scope_stats,
            duration_ms=duration_ms,
            concurrency=concurrency,
            jsonl_path=self._path,
            limit=limit,
            report_path=self.report_path,
        )
