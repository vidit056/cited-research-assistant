import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings, BASE_DIR
from db.models import Base

# Ensure SQLite storage directory exists
if settings.DATABASE_URL.startswith("sqlite"):
    data_dir = BASE_DIR / ".data"
    data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=False
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

def init_db() -> None:
    """Creates all database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for standalone database operations."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
