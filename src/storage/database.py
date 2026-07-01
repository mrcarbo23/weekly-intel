"""Database connection and session management."""
import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from environment, defaulting to SQLite.

    On Vercel the deployment filesystem is read-only except for /tmp, so a
    relative SQLite path fails to open for writes. When DATABASE_URL is not
    set but we're running on Vercel, fall back to a writable /tmp path.
    NOTE: /tmp is ephemeral per-instance — set DATABASE_URL to a managed
    Postgres (Vercel Postgres / Neon) for persistent storage.
    """
    url = os.environ.get("DATABASE_URL")
    if url and url.strip():
        return url.strip()
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


def _sync_missing_columns(eng):
    """Add columns that exist in the models but are missing from existing tables.

    ``create_all`` only creates tables that don't exist yet — it never alters a
    table that predates a model change. When the schema evolves (e.g. a new
    ``sources.url`` column), an older live table keeps failing every query with
    ``UndefinedColumn``. This walks each mapped table and issues a non-destructive
    ``ALTER TABLE ... ADD COLUMN`` for any column the live table is missing.
    Idempotent and safe to run on every init; works on Postgres and SQLite.
    """
    insp = inspect(eng)
    is_postgres = eng.dialect.name == "postgresql"
    existing_tables = set(insp.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # create_all already made it with the full, current schema
        live_columns = insp.get_columns(table.name)
        live_cols = {c["name"] for c in live_columns}
        model_cols = {c.name for c in table.columns}

        # 1. Add columns the model gained but the live table lacks.
        for col in table.columns:
            if col.name in live_cols:
                continue
            col_type = col.type.compile(dialect=eng.dialect)
            ddl = f'ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}'
            try:
                with eng.begin() as conn:
                    conn.execute(text(ddl))
                logger.warning("Schema sync: added missing column %s.%s", table.name, col.name)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Schema sync failed for %s.%s: %s", table.name, col.name, exc)

        # 2. Relax NOT NULL on "orphan" columns the model dropped but the live
        #    table still requires — otherwise inserts fail on a column the app
        #    no longer supplies. Only meaningful on Postgres (SQLite doesn't
        #    enforce these the same way and lacks the ALTER syntax).
        if not is_postgres:
            continue
        for col in live_columns:
            if col["name"] in model_cols or col.get("nullable", True):
                continue
            ddl = f'ALTER TABLE {table.name} ALTER COLUMN {col["name"]} DROP NOT NULL'
            try:
                with eng.begin() as conn:
                    conn.execute(text(ddl))
                logger.warning("Schema sync: dropped NOT NULL on orphan column %s.%s", table.name, col["name"])
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Schema sync failed relaxing %s.%s: %s", table.name, col["name"], exc)


def init_db():
    """Create all tables, then backfill any columns missing from older tables."""
    Base.metadata.create_all(bind=engine)
    _sync_missing_columns(engine)


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
