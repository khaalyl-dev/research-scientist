"""
Database connection layer.

This is the ONE place that knows how to talk to SQLite. Every other module
(agents, CRUD operations, Streamlit pages) imports `get_db_session` from here
rather than creating its own connection — that way we have a single source
of truth for the DB path and connection settings.
"""

import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base

load_dotenv()

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/research.db")

# Make sure the parent folder (data/) exists before SQLite tries to create
# the file — otherwise you get a cryptic "unable to open database file" error.
Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)

# check_same_thread=False is required because Streamlit can call into the DB
# from different threads (e.g. during streaming callbacks). We're a
# single-user MVP so this is safe; it would need revisiting for multi-user.
engine = create_engine(
    f"sqlite:///{SQLITE_PATH}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create all tables if they don't exist yet.

    In dev this is convenient. Once Alembic migrations are set up (next
    task), the real workflow becomes `alembic upgrade head` instead — this
    function stays only as a safety net / for quick tests.
    """
    Base.metadata.create_all(engine)


@contextmanager
def get_db_session():
    """Context-managed DB session — guarantees the session is closed even
    if an error occurs mid-transaction.

    Usage:
        with get_db_session() as db:
            db.add(some_object)
            db.commit()
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
