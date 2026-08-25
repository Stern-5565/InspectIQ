"""Users API tests - same conventions as test_dashboard.py (real DB, no mocks). GET /api/users
was added for the Maintenance module's "assign to" picker (app/api/users.py's own module
docstring) - view-only, no role restriction, company-isolated."""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import auth_headers, delete_user, make_user


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
