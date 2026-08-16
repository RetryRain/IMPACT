from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from clustering.config import get_settings
from clustering.db.models import StoryCluster
from clustering.db.publish_models import SynthesizedStory
from clustering.embedder import embed_texts
from clustering.event_merge import (
    _UnionFind,
    _fold_cluster_into,
    _refresh_cluster_metadata,
    _should_merge_clusters,
    _windows_overlap,
)
from clustering.log import info
from clustering.timezone_util import IST


@dataclass
class _StoryView:
    story: SynthesizedStory
    embedding: np.ndarray
    centroid: np.ndarray = field(repr=False)

    @property
    def id(self) -> uuid.UUID:
        return self.story.id


def _story_window_cluster(story: SynthesizedStory) -> StoryCluster:
    """Adapter so story pairs can reuse cluster window overlap checks."""
    cluster = StoryCluster()
    cluster.first_published_at = story.published_at
    cluster.last_published_at = story.published_at
    return cluster


def _pick_story_survivor(views: list[_StoryView]) -> _StoryView:
    return max(
        views,
        key=lambda view: (
            view.story.priority,
            view.story.published_at or datetime.min.replace(tzinfo=IST),
        ),
    )


@dataclass
class _StoryViewClusterAdapter:
    """Minimal adapter exposing cluster fields for merge helpers."""

    view: _StoryView

    @property
    def cluster(self) -> StoryCluster:
        return _story_window_cluster(self.view.story)

    @property
    def id(self) -> uuid.UUID:
        return self.view.id

    @property
    def title_hint(self) -> str | None:
        return self.view.story.title

    @property
    def embeddings(self) -> list[np.ndarray]:
        return [self.view.embedding]

    @property
    def centroid(self) -> np.ndarray | None:
        return self.view.centroid


def collapse_duplicate_stories(
    publish_session: Session,
    *,
    re_synthesize: bool = False,
) -> dict[str, int]:
    settings = get_settings()
    stories = list(
        publish_session.scalars(
            select(SynthesizedStory).where(
                SynthesizedStory.canonical_story_id.is_(None)
            )
        )
    )
    if len(stories) < 2:
        return {"examined_pairs": 0, "collapsed": 0, "groups": 0}

    texts = [f"{story.title}\n{story.summary or ''}".strip() for story in stories]
    vectors = embed_texts(texts)
    views = [
        _StoryView(story=story, embedding=vectors[index], centroid=vectors[index])
        for index, story in enumerate(stories)
    ]

    by_scope: dict[str | None, list[_StoryView]] = {}
    for view in views:
        by_scope.setdefault(view.story.scope, []).append(view)

    uf = _UnionFind([view.id for view in views])
    examined_pairs = 0

    for scope, scope_views in by_scope.items():
        for index, left in enumerate(scope_views):
            for right in scope_views[index + 1:]:
                left_cluster = _story_window_cluster(left.story)
                right_cluster = _story_window_cluster(right.story)
                if not _windows_overlap(
                    left_cluster,
                    right_cluster,
                    settings.cluster_time_window_hours,
                ):
                    continue
                examined_pairs += 1
                left_adapter = _StoryViewClusterAdapter(left)
                right_adapter = _StoryViewClusterAdapter(right)
                should_merge, _ = _should_merge_clusters(
                    left_adapter,
                    right_adapter,
                    settings=settings,
                )
                if not should_merge:
                    continue
                uf.union(left.id, right.id)

    components: dict[uuid.UUID, list[_StoryView]] = {}
    for view in views:
        root = uf.find(view.id)
        components.setdefault(root, []).append(view)

    collapsed = 0
    for component_views in components.values():
        if len(component_views) < 2:
            continue
        survivor_view = _pick_story_survivor(component_views)
        survivor = publish_session.get(SynthesizedStory, survivor_view.id)
        if survivor is None:
            continue
        for view in component_views:
            if view.id == survivor.id:
                continue
            duplicate = publish_session.get(SynthesizedStory, view.id)
            if duplicate is None:
                continue
            duplicate.canonical_story_id = survivor.id
            collapsed += 1

        if re_synthesize:
            _merge_story_clusters_for_resynthesis(
                survivor,
                [view.story for view in component_views],
            )

    publish_session.flush()
    if collapsed:
        info(f"Collapsed {collapsed} duplicate published story row(s)")
    return {
        "examined_pairs": examined_pairs,
        "collapsed": collapsed,
        "groups": sum(1 for group in components.values() if len(group) >= 2),
    }


def _merge_story_clusters_for_resynthesis(
    survivor: SynthesizedStory,
    group_stories: list[SynthesizedStory],
) -> None:
    from clustering.db.session import get_session
    from clustering.db.models import ClusterStatus

    cluster_ids = {story.cluster_id for story in group_stories}
    if len(cluster_ids) < 2:
        return

    with get_session() as cluster_session:
        survivor_cluster = cluster_session.get(StoryCluster, survivor.cluster_id)
        if survivor_cluster is None:
            return
        for cluster_id in cluster_ids:
            if cluster_id == survivor.cluster_id:
                continue
            victim = cluster_session.get(StoryCluster, cluster_id)
            if victim is None:
                continue
            _fold_cluster_into(cluster_session, survivor_cluster, victim)
        survivor_cluster.status = ClusterStatus.READY_FOR_LLM
        _refresh_cluster_metadata(cluster_session, survivor_cluster)
        cluster_session.commit()

    from clustering.synthesis.worker import synthesize_clusters

    synthesize_clusters(limit=1)
