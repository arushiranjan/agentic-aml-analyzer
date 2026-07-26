"""SQLAlchemy engine, session, and auto-initialization.

Per docs/database.md: SQLite + SQLAlchemy, no separate server required.
Phase 1 creates tables directly via Base.metadata.create_all() on startup
(Alembic migrations are introduced in a later phase per phases.md).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Create all tables if they don't already exist. Called on app startup
    so the database is always ready with zero manual setup steps."""
    from app import models  # noqa: F401  (ensures models are registered on Base)

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency yielding a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
