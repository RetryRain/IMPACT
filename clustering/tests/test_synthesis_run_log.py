from pathlib import Path

from clustering.synthesis.run_log import SynthesisRunLog, format_synthesis_report


def test_synthesis_run_log_writes_summary_only(tmp_path: Path):
    report_path = tmp_path / "synthesis_reports.log"
    log = SynthesisRunLog(path=report_path)

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

    assert written_report == report_path
    report_text = report_path.read_text(encoding="utf-8")
    assert "cluster abc-123" not in report_text
    assert "Clusters examined     : 1" in report_text
    assert "Rewritten             : 1" in report_text
    assert "[India] rewritten=1" in report_text


def test_synthesis_run_log_scope_aggregation_is_thread_safe(tmp_path: Path):
    report_path = tmp_path / "synthesis_reports.log"
    log = SynthesisRunLog(path=report_path)

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

    log.log_summary(
        {"examined": 20, "rewritten": 0, "dropped": 20, "failed": 0, "skipped_existing": 0},
        duration_ms=1000,
        concurrency=4,
    )

    report_text = report_path.read_text(encoding="utf-8")
    assert "[Tamil Nadu] rewritten=0 dropped=20" in report_text


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
        limit=None,
    )

    assert "Clusters examined     : 4" in report
    assert "Skipped (existing)    : 1" in report
    assert "[India] rewritten=1 dropped=1" in report
    assert "[Tamil Nadu] rewritten=0 dropped=1" in report
    assert report.startswith("\n" + "=" * 60)
