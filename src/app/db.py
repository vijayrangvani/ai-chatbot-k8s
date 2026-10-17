"""TEMPLATE: SQLAlchemy 2.0 engine + session-per-request.

Shape to remember:
    engine (how to connect)  ->  SessionLocal (factory)  ->  get_db() yields ONE session per request
    -> route uses it -> commit on success / rollback on error -> always close.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

DB_CONNECT_TIMEOUT_S = 2  # keep below the K8s readinessProbe timeoutSeconds (3)


def connect_args_for(url: str) -> dict:
    """Driver-specific connection options."""
    if url.startswith("sqlite"):
        # SQLite + threads: FastAPI may use the connection from another thread, so allow it.
        return {"check_same_thread": False}
    # Postgres: without this, connecting to an unreachable host can hang for minutes,
    # stalling /ready (and every request) instead of failing fast.
    return {"connect_timeout": DB_CONNECT_TIMEOUT_S}


connect_args = connect_args_for(settings.database_url)

# Engine = connection pool to the database. Create ONCE per process, not per request.
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # check the connection is alive before using it
)

# Session factory. autoflush/autocommit off = YOU decide when to commit.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """All ORM models inherit from this, so Base.metadata knows every table."""


def get_db() -> Generator[Session]:  # Python 3.13+: send/return types default to None
    """FastAPI dependency: `db: Session = Depends(get_db)`.

    `yield` hands the session to the route; code after yield runs when the request ends.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # request finished without error -> save changes
    except Exception:
        db.rollback()  # anything failed -> undo partial changes
        raise  # re-raise so FastAPI still returns the error
    finally:
        db.close()  # ALWAYS return the connection to the pool


# Reusable type alias: write `db: DbSession` in routes instead of `db: Session = Depends(get_db)`.
# Annotated[type, metadata] is FastAPI's recommended style (and avoids a function call in defaults).
DbSession = Annotated[Session, Depends(get_db)]
