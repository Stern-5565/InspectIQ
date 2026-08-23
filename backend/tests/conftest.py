from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.main import app
from app.models.company import Company
from app.models.role import Role
from app.models.user import User, user_roles
from app.security.password import hash_password

TEST_PASSWORD = "Test-Password-123!"


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


def make_user(
    db_session: Session, *, company_name: str, email: str, role_name: str, is_active: bool = True
) -> User:
    """Shared throwaway-user helper for tests that need a real, DB-backed user in a specific
    company/role - e.g. cross-company isolation tests. Not used by test_auth.py, which has its
    own self-contained version predating this one; kept separate deliberately rather than
    risking a refactor of an already-passing test file for marginal DRY benefit."""
    company = db_session.execute(select(Company).where(Company.CompanyName == company_name)).scalar_one()
    role = db_session.execute(select(Role).where(Role.RoleName == role_name)).scalar_one()

    user = User(
        CompanyId=company.CompanyId,
        FirstName="Test",
        LastName="User",
        Email=email,
        PasswordHash=hash_password(TEST_PASSWORD),
        IsActive=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    db_session.execute(user_roles.insert().values(UserId=user.UserId, RoleId=role.RoleId))
    db_session.commit()
    db_session.refresh(user)
    return user


def delete_user(db_session: Session, user: User) -> None:
    db_session.execute(user_roles.delete().where(user_roles.c.UserId == user.UserId))
    db_session.query(User).filter(User.UserId == user.UserId).delete()
    db_session.commit()


def auth_headers(client: TestClient, email: str, password: str = TEST_PASSWORD) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
