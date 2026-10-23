"""Database session and engine management."""

import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from auditor.db.models import Base

# Default to SQLite memory/local if DATABASE_URL not set
DEFAULT_SQLITE_URL = "sqlite:///./auditor_dev.db"


def get_database_url() -> str:
    """Retrieve database connection URL from environment or fallback to default SQLite."""
    return os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)


def create_db_engine(url: str | None = None) -> Engine:
    """Create SQLAlchemy engine with appropriate dialect arguments."""
    db_url = url or get_database_url()
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(db_url, connect_args=connect_args)


class DatabaseSessionManager:
    """Manages database connection lifecycle and session creation."""

    def __init__(self, engine: Engine | None = None):
        self.engine = engine or create_db_engine()
        self.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def init_db(self) -> None:
        """Create all tables in the connected database (for dev/test or bootstrapping)."""
        Base.metadata.create_all(bind=self.engine)

    def drop_db(self) -> None:
        """Drop all tables in the connected database."""
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self) -> Generator[Session, None, None]:
        """Provide a transactional database session scope."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global default manager instance
_default_manager: DatabaseSessionManager | None = None


def get_session_manager(engine: Engine | None = None) -> DatabaseSessionManager:
    """Retrieve or initialize default DatabaseSessionManager."""
    global _default_manager
    if engine is not None:
        return DatabaseSessionManager(engine=engine)
    if _default_manager is None:
        _default_manager = DatabaseSessionManager()
    return _default_manager


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database sessions."""
    manager = get_session_manager()
    yield from manager.get_session()
