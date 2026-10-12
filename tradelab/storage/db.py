"""SQLAlchemy database connection and session management."""

from typing import Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from tradelab.config import get_settings

Base = declarative_base()

_engines: Dict[str, Engine] = {}
_session_factories: Dict[str, sessionmaker] = {}


def get_engine(database_url: Optional[str] = None) -> Engine:
    """Get or create cached SQLAlchemy Engine by database URL."""
    url = database_url or get_settings().database_url
    if url not in _engines:
        if url == "sqlite:///:memory:":
            _engines[url] = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,
            )
        elif url.startswith("sqlite"):
            _engines[url] = create_engine(
                url,
                connect_args={"check_same_thread": False},
                echo=False,
            )
        else:
            _engines[url] = create_engine(url, echo=False)
    return _engines[url]


def get_session(database_url: Optional[str] = None) -> Session:
    """Create a new SQLAlchemy session bound to the target engine."""
    url = database_url or get_settings().database_url
    engine = get_engine(url)
    if url not in _session_factories:
        _session_factories[url] = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return _session_factories[url]()


def init_db(database_url: Optional[str] = None) -> None:
    """Create all tables in the database if they do not exist."""
    # Ensure tables module is imported so models are registered on Base
    import tradelab.storage.tables  # noqa: F401

    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)
