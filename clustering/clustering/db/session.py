from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from clustering.config import get_settings
from clustering.db.models import Base
from clustering.log import info

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
    return _engine


def check_database_connection() -> None:
    settings = get_settings()
    safe_url = settings.database_url
    if "@" in safe_url and "://" in safe_url:
        prefix, rest = safe_url.split("://", 1)
        if "@" in rest and ":" in rest.split("@", 1)[0]:
            creds, hostpart = rest.split("@", 1)
            user = creds.split(":", 1)[0]
            safe_url = f"{prefix}://{user}:***@{hostpart}"
    info(f"Connecting to database ({safe_url}) ...")
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        raise SystemExit(
            "\nCannot connect to PostgreSQL.\n\n"
            "1. Start Postgres (requires Docker Desktop):\n"
            "     docker compose up -d postgres\n\n"
            "2. Run migrations:\n"
            "     cd clustering\n"
            "     alembic upgrade head\n\n"
            "3. Retry your command.\n\n"
            f"Error: {exc}"
        ) from exc
    info("Database connection OK.")


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())
