from __future__ import annotations

import argparse
import json
import sys
import uuid

from clustering.assigner import (
    assign_articles,
    get_cluster_payload,
    mark_ready_clusters,
)
from clustering.db.publish_session import check_publish_database_connection
from clustering.db.session import check_database_connection, get_session
from clustering.embedder import embed_articles
from clustering.ingest import ingest_json_file
from clustering.log import configure_logging, info, stage
from clustering.synthesis.worker import synthesize_clusters


def _cmd_ingest(args: argparse.Namespace) -> int:
    check_database_connection()
    stage("Ingest")
    with get_session() as session:
        stats = ingest_json_file(session, args.file)
    print(json.dumps(stats, indent=2))
    return 0


def _cmd_embed(args: argparse.Namespace) -> int:
    check_database_connection()
    stage("Embed")
    with get_session() as session:
        stats = embed_articles(session, limit=args.limit)
    print(json.dumps(stats, indent=2))
    return 0


def _cmd_assign(args: argparse.Namespace) -> int:
    check_database_connection()
    stage("Assign")
    with get_session() as session:
        stats = assign_articles(session, limit=args.limit)
        ready_stats = mark_ready_clusters(session, force=args.force_ready)
    print(json.dumps({**stats, **ready_stats}, indent=2))
    return 0


def _cmd_process(args: argparse.Namespace) -> int:
    check_database_connection()

    stage("Ingest")
    with get_session() as session:
        ingest_stats = ingest_json_file(session, args.file)

    stage("Embed")
    with get_session() as session:
        embed_stats = embed_articles(session, limit=args.limit)

    stage("Assign")
    with get_session() as session:
        assign_stats = assign_articles(session, limit=args.limit)
        ready_stats = mark_ready_clusters(session, force=args.force_ready)

    info("\nDone.")
    print(
        json.dumps(
            {
                "ingest": ingest_stats,
                "embed": embed_stats,
                "assign": assign_stats,
                "ready": ready_stats,
            },
            indent=2,
        )
    )
    return 0


def _cmd_show_cluster(args: argparse.Namespace) -> int:
    check_database_connection()
    cluster_id = uuid.UUID(args.cluster_id)
    with get_session() as session:
        payload = get_cluster_payload(session, cluster_id)
    print(json.dumps(payload, indent=2))
    return 0


def _cmd_synthesize(args: argparse.Namespace) -> int:
    check_database_connection()
    check_publish_database_connection()
    stage("Synthesize")
    stats = synthesize_clusters(limit=args.limit)
    print(json.dumps(stats, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bytez-cluster",
        description="Semantic duplicate detection and story clustering",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress messages (JSON output only)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest Scrapy JSON export")
    ingest_parser.add_argument("--file", required=True, help="Path to data.json")
    ingest_parser.set_defaults(func=_cmd_ingest)

    embed_parser = subparsers.add_parser("embed", help="Embed articles missing vectors")
    embed_parser.add_argument("--limit", type=int, default=None)
    embed_parser.set_defaults(func=_cmd_embed)

    assign_parser = subparsers.add_parser("assign", help="Assign articles to clusters")
    assign_parser.add_argument("--limit", type=int, default=None)
    assign_parser.add_argument(
        "--force-ready",
        action="store_true",
        help="Mark all open clusters ready_for_llm after assignment",
    )
    assign_parser.set_defaults(func=_cmd_assign)

    process_parser = subparsers.add_parser(
        "process", help="Ingest, embed, and assign in one run"
    )
    process_parser.add_argument("--file", required=True, help="Path to data.json")
    process_parser.add_argument("--limit", type=int, default=None)
    process_parser.add_argument("--force-ready", action="store_true")
    process_parser.set_defaults(func=_cmd_process)

    show_parser = subparsers.add_parser("show-cluster", help="Show cluster payload")
    show_parser.add_argument("cluster_id", help="Cluster UUID")
    show_parser.set_defaults(func=_cmd_show_cluster)

    synthesize_parser = subparsers.add_parser(
        "synthesize", help="Rewrite ready_for_llm clusters via OpenRouter"
    )
    synthesize_parser.add_argument("--limit", type=int, default=None)
    synthesize_parser.set_defaults(func=_cmd_synthesize)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
