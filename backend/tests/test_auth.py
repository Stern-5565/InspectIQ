"""
Authentication tests. Every test hits the real local InspectIQDb - no mocks, matching the
convention validated throughout PropertyManager. Test users are throwaway rows created against
the already-seeded 'Northgate Property Management' demo company and explicitly cleaned up in
the fixture's teardown (try/finally style), not left behind and not relying on transaction
rollback fixtures - same pattern PropertyManager used successfully across 4+ modules.
"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.role import Role
from app.models.user import User, user_roles
from app.security.password import hash_password

TEST_PASSWORD = "Test-Password-123!"


def _make_user(db_session: Session, *, email: str, role_name: str, is_active: bool = True) -> User:
    company = db_session.execute(
        select(Company).where(Company.CompanyName == "Northgate Property Management")
    ).scalar_one()
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


def _delete_user(db_session: Session, user: User) -> None:
    db_session.execute(user_roles.delete().where(user_roles.c.UserId == user.UserId))
    db_session.query(User).filter(User.UserId == user.UserId).delete()
    db_session.commit()


@pytest.fixture
def active_user(db_session: Session) -> Generator[User, None, None]:
    user = _make_user(db_session, email="test.active.tmp@example.com", role_name="Inspector")
    yield user
    _delete_user(db_session, user)


@pytest.fixture
def inactive_user(db_session: Session) -> Generator[User, None, None]:
    user = _make_user(
        db_session, email="test.inactive.tmp@example.com", role_name="Inspector", is_active=False
    )
    yield user
    _delete_user(db_session, user)


# --- login ------------------------------------------------------------------------------

def test_login_with_valid_credentials_returns_tokens(client: TestClient, active_user: User) -> None:
    response = client.post(
        "/api/auth/login", json={"email": active_user.Email, "password": TEST_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_with_wrong_password_returns_401(client: TestClient, active_user: User) -> None:
    response = client.post(
        "/api/auth/login", json={"email": active_user.Email, "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_login_with_nonexistent_email_returns_401_with_same_message_as_wrong_password(
    client: TestClient, active_user: User
) -> None:
    wrong_password_response = client.post(
        "/api/auth/login", json={"email": active_user.Email, "password": "wrong-password"}
    )
    nonexistent_email_response = client.post(
        "/api/auth/login", json={"email": "no.such.user@example.com", "password": "whatever"}
    )

    assert nonexistent_email_response.status_code == 401
    # Same message either way - don't let the response reveal whether the email exists.
    assert nonexistent_email_response.json() == wrong_password_response.json()


def test_login_with_inactive_user_returns_401(client: TestClient, inactive_user: User) -> None:
    response = client.post(
        "/api/auth/login", json={"email": inactive_user.Email, "password": TEST_PASSWORD}
    )

    assert response.status_code == 401


# --- /me ----------------------------------------------------------------------------------

def test_me_returns_current_user_with_valid_token(client: TestClient, active_user: User) -> None:
    login_response = client.post(
        "/api/auth/login", json={"email": active_user.Email, "password": TEST_PASSWORD}
    )
    access_token = login_response.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["UserId"] == active_user.UserId
    assert body["Email"] == active_user.Email
    assert body["Roles"] == ["Inspector"]
    assert "PasswordHash" not in body


def test_me_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_rejects_garbage_token(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_deactivated_user_token_rejected_on_next_request(
    client: TestClient, db_session: Session, active_user: User
) -> None:
    """The security-critical case: an already-issued access token must stop working the
    instant its user is deactivated mid-session, not just once the token naturally expires -
    proves get_current_user re-checks IsActive from the DB every request rather than trusting
    the token payload. Same case that caught a real bug in PropertyManager."""
    login_response = client.post(
        "/api/auth/login", json={"email": active_user.Email, "password": TEST_PASSWORD}
    )
    access_token = login_response.json()["access_token"]

    # Confirm the token works before deactivation.
    ok_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert ok_response.status_code == 200

    db_session.query(User).filter(User.UserId == active_user.UserId).update({"IsActive": False})
    db_session.commit()

    rejected_response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert rejected_response.status_code == 401


# --- refresh ------------------------------------------------------------------------------

def test_refresh_with_valid_refresh_token_returns_new_tokens(
    client: TestClient, active_user: User
) -> None:
    login_response = client.post(
        "/api/auth/login", json={"email": active_user.Email, "password": TEST_PASSWORD}
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_rejects_an_access_token_used_as_a_refresh_token(
    client: TestClient, active_user: User
) -> None:
    """Guards against token-type confusion - an access token must not work where a refresh
    token is expected, even though both are structurally valid JWTs signed with the same key."""
    login_response = client.post(
        "/api/auth/login", json={"email": active_user.Email, "password": TEST_PASSWORD}
    )
    access_token = login_response.json()["access_token"]

    response = client.post("/api/auth/refresh", json={"refresh_token": access_token})

    assert response.status_code == 401


# --- role-based authorization -------------------------------------------------------------

def test_require_roles_rejects_user_without_the_required_role(active_user: User) -> None:
    """active_user has the Inspector role only (assigned via the real UserRoles table in the
    fixture). No role-gated business endpoint exists yet (that starts in Phase 6+), so this
    calls the dependency function directly - FastAPI dependencies are plain functions, and
    Depends() only matters when FastAPI's own DI resolves them, so calling it straight is a
    legitimate way to exercise the real role-intersection logic against a real DB-loaded user
    without needing a live protected route or a mock."""
    from app.core.exceptions import ForbiddenError
    from app.security import roles
    from app.security.dependencies import require_roles

    dependency = require_roles(roles.ADMINISTRATOR)

    with pytest.raises(ForbiddenError):
        dependency(current_user=active_user)


def test_require_roles_allows_user_with_the_required_role(active_user: User) -> None:
    from app.security import roles
    from app.security.dependencies import require_roles

    dependency = require_roles(roles.INSPECTOR)

    assert dependency(current_user=active_user) is active_user
