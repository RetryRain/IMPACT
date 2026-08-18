import json
from pathlib import Path

import pytest

from clustering.synthesis.run_log import SynthesisRunLog, format_synthesis_report


def test_synthesis_run_log_writes_cluster_and_summary(tmp_path: Path):
    log_path = tmp_path / "synthesis.jsonl"
    report_path = tmp_path / "synthesis_reports.log"
    log = SynthesisRunLog(path=log_path, report_path=report_path)

    log.log_cluster(
        cluster_id="abc-123",
        outcome="rewritten",
        action="rewrite",
        scope="India",
        priority=80,
        title="Test headline",
        duration_ms=1500,
    )
    written_report = log.log_summary(
        {"examined": 1, "rewritten": 1, "dropped": 0, "failed": 0, "skipped_existing": 0},
        duration_ms=2000,
        concurrency=1,
        limit=10,
    )

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    cluster_entry = json.loads(lines[0])
    assert cluster_entry["type"] == "cluster"
    assert cluster_entry["cluster_id"] == "abc-123"
    assert cluster_entry["outcome"] == "rewritten"
    assert cluster_entry["scope"] == "India"
    assert cluster_entry["priority"] == 80
    assert cluster_entry["title"] == "Test headline"
    assert cluster_entry["duration_ms"] == 1500
    assert "timestamp" in cluster_entry
    assert "provider" in cluster_entry

    summary_entry = json.loads(lines[1])
    assert summary_entry["type"] == "summary"
    assert summary_entry["stats"]["rewritten"] == 1
    assert summary_entry["duration_ms"] == 2000
    assert summary_entry["concurrency"] == 1

    assert written_report == report_path
    report_text = report_path.read_text(encoding="utf-8")
    assert "Clusters examined     : 1" in report_text
    assert "Rewritten             : 1" in report_text
    assert "[India] rewritten=1" in report_text

    stats_path = tmp_path / "synthesis_stats.jsonl"
    stats_line = json.loads(stats_path.read_text(encoding="utf-8").strip())
    assert stats_line["rewritten"] == 1
    assert stats_line["clusters_examined"] == 1


def test_synthesis_run_log_is_thread_safe(tmp_path: Path):
    log_path = tmp_path / "synthesis.jsonl"
    log = SynthesisRunLog(path=log_path)

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(
                log.log_cluster,
                cluster_id=f"id-{index}",
                outcome="dropped",
                action="drop",
                assigned_scope="Tamil Nadu",
                drop_reason="test",
            )
            for index in range(20)
        ]
        for future in futures:
            future.result()

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 20


def test_format_synthesis_report_includes_scope_block():
    report = format_synthesis_report(
        stats={
            "examined": 4,
            "rewritten": 1,
            "dropped": 2,
            "failed": 0,
            "skipped_existing": 1,
        },
        scope_stats={
            "India": {"rewritten": 1, "dropped": 1, "failed": 0, "skipped_existing": 0},
            "Tamil Nadu": {"rewritten": 0, "dropped": 1, "failed": 0, "skipped_existing": 1},
        },
        duration_ms=4500,
        concurrency=3,
        provider="deepseek",
        model="deepseek-chat",
        jsonl_path=Path("logs/synthesis.jsonl"),
        limit=None,
    )

    assert "Clusters examined     : 4" in report
    assert "Skipped (existing)    : 1" in report
    assert "[India] rewritten=1 dropped=1" in report
    assert "[Tamil Nadu] rewritten=0 dropped=1" in report
    assert report.startswith("\n" + "=" * 60)
