"""Database connection and session management."""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base


def get_database_url() -> str:
    """Get database URL from environment, defaulting to SQLite.

    On Vercel the deployment filesystem is read-only except for /tmp, so a
    relative SQLite path fails to open for writes. When DATABASE_URL is not
    set but we're running on Vercel, fall back to a writable /tmp path.
    NOTE: /tmp is ephemeral per-instance — set DATABASE_URL to a managed
    Postgres (Vercel Postgres / Neon) for persistent storage.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    if os.environ.get("VERCEL"):
        return "sqlite:////tmp/weekly_intel.db"
    return "sqlite:///./weekly_intel.db"


def create_db_engine(database_url: str = None):
    url = database_url or get_database_url()
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
