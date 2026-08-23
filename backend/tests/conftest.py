from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Real DB session for test setup/teardown - no mocks, same convention used throughout
    PropertyManager."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
