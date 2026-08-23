"""SQLAlchemy engine/session setup and the FastAPI DB dependency."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import models  # noqa: F401 - import registers every mapped class (see models/__init__.py)
from app.core.config import settings

engine = create_engine(
    settings.sqlalchemy_database_uri,
    echo=settings.APP_DEBUG,
    pool_pre_ping=True,
    fast_executemany=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
