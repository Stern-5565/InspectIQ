"""Users API tests - same conventions as test_dashboard.py (real DB, no mocks). GET /api/users
was added for the Maintenance module's "assign to" picker (app/api/users.py's own module
docstring) - view-only, no role restriction, company-isolated. POST/PATCH are Admin Settings'
own addition (see app/services/user_service.py's module docstring) - Administrator-only, the
first tier in this project that excludes Manager."""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import auth_headers, delete_user, make_user


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.users.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_manager(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.users.manager.tmp@example.com",
        role_name="Manager",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_viewer(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.users.viewer.tmp@example.com",
        role_name="Viewer",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.users.bsadmin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


def _delete_created_user(db_session: Session, user_id: int) -> None:
    from app.models.user import User, user_roles

    db_session.execute(user_roles.delete().where(user_roles.c.UserId == user_id))
    db_session.query(User).filter(User.UserId == user_id).delete()
    db_session.commit()


def test_list_users_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/users")
    assert response.status_code == 401


def test_list_users_open_to_viewer_role(client: TestClient, northgate_viewer) -> None:
    """Viewer is the most restricted role everywhere else in this project - confirming it can
    still list company users is the real check that "view = any company member" holds here too."""
    response = client.get("/api/users", headers=auth_headers(client, northgate_viewer.Email))
    assert response.status_code == 200
    emails = {u["Email"] for u in response.json()}
    assert "admin@northgatepm.example" in emails
    assert "PasswordHash" not in response.json()[0]


def test_list_users_isolates_by_company(client: TestClient, bright_spaces_admin) -> None:
    response = client.get("/api/users", headers=auth_headers(client, bright_spaces_admin.Email))
    assert response.status_code == 200
    emails = {u["Email"] for u in response.json()}
    assert "admin@northgatepm.example" not in emails
    assert "admin@brightspaces.example" in emails


# --- create --------------------------------------------------------------------------------


def test_create_user_as_admin_succeeds_and_new_user_can_log_in(
    client: TestClient, db_session: Session, northgate_admin
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    response = client.post(
        "/api/users",
        json={
            "FirstName": "New",
            "LastName": "Inspector",
            "Email": "test.users.newinspector.tmp@example.com",
            "Phone": "07700900000",
            "Password": "Password123!",
            "RoleName": "Inspector",
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["Roles"] == ["Inspector"]
    assert body["IsActive"] is True
    assert "Password" not in body and "PasswordHash" not in body
    user_id = body["UserId"]

    try:
        login = client.post(
            "/api/auth/login",
            json={"email": "test.users.newinspector.tmp@example.com", "password": "Password123!"},
        )
        assert login.status_code == 200
    finally:
        _delete_created_user(db_session, user_id)


def test_create_user_duplicate_email_returns_409(client: TestClient, northgate_admin) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    response = client.post(
        "/api/users",
        json={
            "FirstName": "Dup",
            "LastName": "User",
            "Email": "admin@northgatepm.example",
            "Password": "Password123!",
            "RoleName": "Viewer",
        },
        headers=headers,
    )
    assert response.status_code == 409


def test_create_user_with_unknown_role_returns_422(client: TestClient, northgate_admin) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    response = client.post(
        "/api/users",
        json={
            "FirstName": "Bad",
            "LastName": "Role",
            "Email": "test.users.badrole.tmp@example.com",
            "Password": "Password123!",
            "RoleName": "SuperUser",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_create_user_as_manager_returns_403(client: TestClient, northgate_manager) -> None:
    """Confirms the Admin-only tier really excludes Manager - unlike every other "narrower than
    any company member" tier in this project, which still includes Manager alongside
    Administrator."""
    headers = auth_headers(client, northgate_manager.Email)
    response = client.post(
        "/api/users",
        json={
            "FirstName": "Should",
            "LastName": "Fail",
            "Email": "test.users.shouldfail.tmp@example.com",
            "Password": "Password123!",
            "RoleName": "Viewer",
        },
        headers=headers,
    )
    assert response.status_code == 403


# --- update --------------------------------------------------------------------------------


def test_update_user_changes_role_and_deactivates(
    client: TestClient, db_session: Session, northgate_admin
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    create = client.post(
        "/api/users",
        json={
            "FirstName": "To",
            "LastName": "Update",
            "Email": "test.users.toupdate.tmp@example.com",
            "Password": "Password123!",
            "RoleName": "Viewer",
        },
        headers=headers,
    )
    user_id = create.json()["UserId"]

    try:
        response = client.patch(
            f"/api/users/{user_id}",
            json={"RoleName": "Manager", "IsActive": False},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["Roles"] == ["Manager"]
        assert body["IsActive"] is False
    finally:
        _delete_created_user(db_session, user_id)


def test_update_user_cannot_deactivate_own_account(client: TestClient, northgate_admin) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    response = client.patch(
        f"/api/users/{northgate_admin.UserId}",
        json={"IsActive": False},
        headers=headers,
    )
    assert response.status_code == 422


def test_update_user_as_manager_returns_403(client: TestClient, northgate_manager, northgate_viewer) -> None:
    response = client.patch(
        f"/api/users/{northgate_viewer.UserId}",
        json={"IsActive": False},
        headers=auth_headers(client, northgate_manager.Email),
    )
    assert response.status_code == 403


def test_update_user_in_another_company_returns_404(client: TestClient, northgate_admin, bright_spaces_admin) -> None:
    response = client.patch(
        f"/api/users/{bright_spaces_admin.UserId}",
        json={"IsActive": False},
        headers=auth_headers(client, northgate_admin.Email),
    )
    assert response.status_code == 404
