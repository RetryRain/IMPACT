import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from clustering.assigner import assign_articles, get_cluster_payload
from clustering.config import get_settings
from clustering.db.models import Article, Base, StoryCluster
from clustering.embedder import embed_articles, set_model
from clustering.ingest import ingest_json_file
from tests.fixtures import FakeModel

pytestmark = pytest.mark.integration


def _database_url() -> str | None:
    url = get_settings().database_url
    if not url.startswith("postgresql"):
        return None
    return url


@pytest.fixture
def pg_session():
    url = _database_url()
    if url is None:
        pytest.skip("PostgreSQL DATABASE_URL required for integration tests")

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL unavailable: {exc}")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = factory()
    set_model(FakeModel())
    try:
        yield db
        db.commit()
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_ingest_json_upserts_on_url(pg_session, tmp_path: Path):
    items = [
        {
            "url": "https://example.com/a",
            "title": "First",
            "scope": "India",
            "published_at": "2026-08-05T10:00:00+00:00",
        },
        {
            "url": "https://example.com/a",
            "title": "Updated",
            "scope": "India",
            "published_at": "2026-08-05T11:00:00+00:00",
        },
    ]
    path = tmp_path / "data.json"
    path.write_text(json.dumps(items), encoding="utf-8")

    first = ingest_json_file(pg_session, path)
    second = ingest_json_file(pg_session, path)

    assert first == {"created": 1, "updated": 0, "skipped": 0}
    assert second == {"created": 0, "updated": 1, "skipped": 0}
    assert len(list(pg_session.scalars(select(Article)))) == 1
    assert pg_session.scalar(select(Article)).title == "Updated"


def _add_article(session, *, url: str, title: str, source: str, published_at: datetime):
    article = Article(
        url=url,
        title=title,
        summary=title,
        body=title,
        source=source,
        scope="India",
        language="en",
        published_at=published_at,
    )
    session.add(article)
    session.flush()
    return article


def test_assigner_groups_similar_cross_source_articles(pg_session):
    t0 = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    a1 = _add_article(
        pg_session,
        url="https://hindu.com/1",
        title="Cabinet approves new policy on renewable energy targets",
        source="The Hindu",
        published_at=t0,
    )
    a2 = _add_article(
        pg_session,
        url="https://toi.com/1",
        title="Cabinet clears renewable energy policy with new targets",
        source="Times of India",
        published_at=t0,
    )
    a3 = _add_article(
        pg_session,
        url="https://ie.com/1",
        title="Cricket team announces squad for upcoming test series",
        source="Indian Express",
        published_at=t0,
    )

    pg_session.commit()
    embed_articles(pg_session)
    stats = assign_articles(pg_session)

    assert stats["examined"] == 3
    pg_session.refresh(a1)
    pg_session.refresh(a2)
    pg_session.refresh(a3)
    assert a1.cluster_id is not None
    assert a2.cluster_id is not None
    assert a3.cluster_id is not None
    assert a3.cluster_id != a1.cluster_id or a3.cluster_id != a2.cluster_id


def test_get_cluster_payload_shape(pg_session):
    t0 = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    article = _add_article(
        pg_session,
        url="https://example.com/x",
        title="Sample",
        source="The Hindu",
        published_at=t0,
    )
    cluster = StoryCluster(
        representative_article_id=article.id,
        title_hint=article.title,
        scope="India",
        first_published_at=t0,
        last_published_at=t0,
        article_count=1,
    )
    pg_session.add(cluster)
    pg_session.flush()
    article.cluster_id = cluster.id
    pg_session.commit()

    payload = get_cluster_payload(pg_session, cluster.id)
    assert payload["cluster_id"] == str(cluster.id)
    assert payload["scope"] == "India"
    assert len(payload["articles"]) == 1
    assert payload["articles"][0]["source"] == "The Hindu"
