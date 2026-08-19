from __future__ import annotations

import json
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from clustering.config import get_settings
from clustering.db.models import Article, ClusterStatus, StoryCluster
from clustering.log import info
from clustering.timezone_util import IST

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "he",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "was",
        "were",
        "will",
        "with",
    }
)


def title_tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {word for word in words if len(word) > 2 and word not in _STOPWORDS}


def title_jaccard(a: str | None, b: str | None) -> tuple[float, int]:
    ta = title_tokens(a)
    tb = title_tokens(b)
    if not ta or not tb:
        return 0.0, 0
    inter = ta & tb
    union = ta | tb
    return len(inter) / len(union), len(inter)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def mean_centroid(vectors: list[np.ndarray]) -> np.ndarray | None:
    if not vectors:
        return None
    stacked = np.stack(vectors, axis=0)
    centroid = stacked.mean(axis=0)
    norm = np.linalg.norm(centroid)
    if norm == 0:
        return None
    return centroid / norm


@dataclass
class _ClusterView:
    cluster: StoryCluster
    embeddings: list[np.ndarray] = field(default_factory=list)
    centroid: np.ndarray | None = None

    @property
    def id(self) -> uuid.UUID:
        return self.cluster.id

    @property
    def title_hint(self) -> str | None:
        return self.cluster.title_hint


class _UnionFind:
    def __init__(self, ids: list[uuid.UUID]) -> None:
        self.parent = {cluster_id: cluster_id for cluster_id in ids}

    def find(self, cluster_id: uuid.UUID) -> uuid.UUID:
        root = cluster_id
        while self.parent[root] != root:
            self.parent[root] = self.parent[self.parent[root]]
            root = self.parent[root]
        return root

    def union(self, left: uuid.UUID, right: uuid.UUID) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


class EventMergeLog:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = Path(__file__).resolve().parents[2] / "logs" / "event_merge.log"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, entry: dict[str, Any]) -> None:
        timestamp = entry.get("timestamp")
        if not isinstance(timestamp, str):
            timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %Z")

        entry_type = entry.get("type", "event")
        if entry_type == "pair":
            line = (
                f"[{timestamp}] pair scope={entry.get('scope')} "
                f"{entry.get('from_cluster_id')} -> {entry.get('to_cluster_id')} "
                f"reasons={entry.get('reasons')} "
                f"centroid={entry.get('centroid_similarity')} "
                f"pairwise={entry.get('max_pairwise_similarity')} "
                f"jaccard={entry.get('title_jaccard')}"
            )
        elif entry_type == "merge":
            line = (
                f"[{timestamp}] merge scope={entry.get('scope')} "
                f"{entry.get('from_cluster_id')} -> {entry.get('to_cluster_id')}"
            )
        else:
            line = f"[{timestamp}] {entry_type} {entry}"

        with self._lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")


def _windows_overlap(
    left: StoryCluster,
    right: StoryCluster,
    window_hours: int,
) -> bool:
    if left.first_published_at is None or right.first_published_at is None:
        return False
    window = timedelta(hours=window_hours)
    left_start = left.first_published_at - window
    left_end = (left.last_published_at or left.first_published_at) + window
    right_start = right.first_published_at - window
    right_end = (right.last_published_at or right.first_published_at) + window
    return left_start <= right_end and right_start <= left_end


def _max_pairwise_similarity(
    left_embeddings: list[np.ndarray],
    right_embeddings: list[np.ndarray],
) -> float:
    best = -1.0
    for left in left_embeddings:
        for right in right_embeddings:
            best = max(best, cosine_similarity(left, right))
    return best


def _should_merge_clusters(
    left: _ClusterView,
    right: _ClusterView,
    *,
    settings,
) -> tuple[bool, dict[str, Any]]:
    centroid_sim = -1.0
    if left.centroid is not None and right.centroid is not None:
        centroid_sim = cosine_similarity(left.centroid, right.centroid)

    max_pair = _max_pairwise_similarity(left.embeddings, right.embeddings)
    jaccard, shared_tokens = title_jaccard(left.title_hint, right.title_hint)

    reasons: list[str] = []
    if centroid_sim >= settings.event_merge_threshold:
        reasons.append("centroid")
    if max_pair >= settings.similarity_threshold:
        reasons.append("pairwise")
    if (
        centroid_sim >= settings.event_merge_soft_threshold
        and jaccard >= settings.event_merge_title_jaccard
        and shared_tokens >= 2
    ):
        reasons.append("title_soft")

    return bool(reasons), {
        "centroid_similarity": round(centroid_sim, 4),
        "max_pairwise_similarity": round(max_pair, 4),
        "title_jaccard": round(jaccard, 4),
        "shared_title_tokens": shared_tokens,
        "reasons": reasons,
    }


def _pick_survivor(views: list[_ClusterView]) -> _ClusterView:
    return max(
        views,
        key=lambda view: (
            view.cluster.article_count,
            view.cluster.last_published_at or datetime.min.replace(tzinfo=IST),
        ),
    )


def _refresh_cluster_metadata(session: Session, cluster: StoryCluster) -> None:
    articles = list(
        session.scalars(
            select(Article)
            .where(Article.cluster_id == cluster.id)
            .order_by(Article.published_at.asc().nulls_last(), Article.created_at.asc())
        )
    )
    cluster.article_count = len(articles)
    if not articles:
        cluster.first_published_at = None
        cluster.last_published_at = None
        cluster.representative_article_id = None
        cluster.title_hint = None
        return

    cluster.first_published_at = min(
        (article.published_at for article in articles if article.published_at),
        default=None,
    )
    cluster.last_published_at = max(
        (article.published_at for article in articles if article.published_at),
        default=None,
    )
    representative = min(
        articles,
        key=lambda article: (
            article.published_at or datetime.max.replace(tzinfo=IST),
            article.created_at,
        ),
    )
    cluster.representative_article_id = representative.id
    cluster.title_hint = representative.title
    cluster.status = ClusterStatus.OPEN


def _fold_cluster_into(
    session: Session,
    survivor: StoryCluster,
    victim: StoryCluster,
) -> None:
    for article in session.scalars(select(Article).where(Article.cluster_id == victim.id)):
        article.cluster_id = survivor.id
    session.delete(victim)
    _refresh_cluster_metadata(session, survivor)


def merge_event_clusters(
    session: Session,
    *,
    merge_log: EventMergeLog | None = None,
) -> dict[str, int]:
    settings = get_settings()
    log = merge_log or EventMergeLog()

    clusters = list(
        session.scalars(
            select(StoryCluster)
            .where(
                StoryCluster.status.in_(
                    [ClusterStatus.OPEN, ClusterStatus.READY_FOR_LLM]
                )
            )
            .options(joinedload(StoryCluster.articles).joinedload(Article.embedding))
        ).unique()
    )

    views: list[_ClusterView] = []
    for cluster in clusters:
        embeddings: list[np.ndarray] = []
        for article in cluster.articles:
            if article.embedding is None:
                continue
            embeddings.append(np.asarray(article.embedding.embedding, dtype=np.float32))
        view = _ClusterView(
            cluster=cluster,
            embeddings=embeddings,
            centroid=mean_centroid(embeddings),
        )
        if view.centroid is not None:
            views.append(view)

    if len(views) < 2:
        return {"examined_pairs": 0, "merged_clusters": 0, "components": 0}

    by_scope: dict[str | None, list[_ClusterView]] = {}
    for view in views:
        by_scope.setdefault(view.cluster.scope, []).append(view)

    uf = _UnionFind([view.id for view in views])
    examined_pairs = 0

    for scope, scope_views in by_scope.items():
        for index, left in enumerate(scope_views):
            for right in scope_views[index + 1:]:
                if not _windows_overlap(
                    left.cluster,
                    right.cluster,
                    settings.cluster_time_window_hours,
                ):
                    continue
                examined_pairs += 1
                should_merge, scores = _should_merge_clusters(left, right, settings=settings)
                if not should_merge:
                    continue
                uf.union(left.id, right.id)
                log.write(
                    {
                        "type": "pair",
                        "timestamp": datetime.now(IST).isoformat(),
                        "from_cluster_id": str(right.id),
                        "to_cluster_id": str(left.id),
                        "scope": scope,
                        **scores,
                    }
                )

    components: dict[uuid.UUID, list[_ClusterView]] = {}
    for view in views:
        root = uf.find(view.id)
        components.setdefault(root, []).append(view)

    merged_clusters = 0
    for component_views in components.values():
        if len(component_views) < 2:
            continue
        survivor_view = _pick_survivor(component_views)
        survivor = session.get(StoryCluster, survivor_view.id)
        if survivor is None:
            continue
        for view in component_views:
            if view.id == survivor.id:
                continue
            victim = session.get(StoryCluster, view.id)
            if victim is None:
                continue
            _fold_cluster_into(session, survivor, victim)
            merged_clusters += 1
            log.write(
                {
                    "type": "merge",
                    "timestamp": datetime.now(IST).isoformat(),
                    "from_cluster_id": str(victim.id),
                    "to_cluster_id": str(survivor.id),
                    "scope": survivor.scope,
                }
            )

    if merged_clusters:
        info(f"Event merge folded {merged_clusters} cluster(s) into survivors")
    session.flush()
    return {
        "examined_pairs": examined_pairs,
        "merged_clusters": merged_clusters,
        "components": len(components),
    }
