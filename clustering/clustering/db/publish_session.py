from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from clustering.config import get_settings
from clustering.log import info

_publish_engine = None
_PublishSessionLocal = None


def _safe_url(url: str) -> str:
    if "@" in url and "://" in url:
        prefix, rest = url.split("://", 1)
        if "@" in rest and ":" in rest.split("@", 1)[0]:
            creds, hostpart = rest.split("@", 1)
            user = creds.split(":", 1)[0]
            return f"{prefix}://{user}:***@{hostpart}"
    return url


def get_publish_engine():
    global _publish_engine
    if _publish_engine is None:
        settings = get_settings()
        _publish_engine = create_engine(
            settings.synthesis_database_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
    return _publish_engine


def check_publish_database_connection() -> None:
    settings = get_settings()
    safe_url = _safe_url(settings.synthesis_database_url)
    info(f"Connecting to publish database ({safe_url}) ...")
    try:
        with get_publish_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        raise SystemExit(
            "\nCannot connect to publish PostgreSQL.\n\n"
            "1. Set SYNTHESIS_DATABASE_URL in .env\n"
            "2. Run publish migrations:\n"
            "     cd clustering\n"
            "     alembic -c alembic_publish.ini upgrade head\n\n"
            "3. Retry your command.\n\n"
            f"Error: {exc}"
        ) from exc
    info("Publish database connection OK.")


def get_publish_session_factory() -> sessionmaker[Session]:
    global _PublishSessionLocal
    if _PublishSessionLocal is None:
        _PublishSessionLocal = sessionmaker(
            bind=get_publish_engine(),
            autoflush=False,
            expire_on_commit=False,
        )
    return _PublishSessionLocal


@contextmanager
def get_publish_session() -> Generator[Session, None, None]:
    session = get_publish_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
