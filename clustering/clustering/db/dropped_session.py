from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from clustering.config import get_settings
from clustering.log import info

_dropped_engine = None
_DroppedSessionLocal = None


def _safe_url(url: str) -> str:
    if "@" in url and "://" in url:
        prefix, rest = url.split("://", 1)
        if "@" in rest and ":" in rest.split("@", 1)[0]:
            creds, hostpart = rest.split("@", 1)
            user = creds.split(":", 1)[0]
            return f"{prefix}://{user}:***@{hostpart}"
    return url


def get_dropped_engine():
    global _dropped_engine
    if _dropped_engine is None:
        settings = get_settings()
        _dropped_engine = create_engine(
            settings.dropped_articles_database_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
    return _dropped_engine


def check_dropped_database_connection() -> None:
    settings = get_settings()
    safe_url = _safe_url(settings.dropped_articles_database_url)
    info(f"Connecting to dropped-articles database ({safe_url}) ...")
    try:
        with get_dropped_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        raise SystemExit(
            "\nCannot connect to dropped-articles PostgreSQL.\n\n"
            "1. Set DROPPED_ARTICLES_DATABASE_URL in .env\n"
            "2. Run dropped migrations:\n"
            "     cd clustering\n"
            "     alembic -c alembic_dropped.ini upgrade head\n\n"
            "3. Retry your command.\n\n"
            f"Error: {exc}"
        ) from exc
    info("Dropped-articles database connection OK.")


def get_dropped_session_factory() -> sessionmaker[Session]:
    global _DroppedSessionLocal
    if _DroppedSessionLocal is None:
        _DroppedSessionLocal = sessionmaker(
            bind=get_dropped_engine(),
            autoflush=False,
            expire_on_commit=False,
        )
    return _DroppedSessionLocal


@contextmanager
def get_dropped_session() -> Generator[Session, None, None]:
    session = get_dropped_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
