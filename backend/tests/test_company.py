"""Company Profile API tests - same conventions as test_users.py (real DB, no mocks). GET is
view-only, no role restriction; PATCH is Administrator-only, per
app/services/company_service.py's module docstring."""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.company import Company
from tests.conftest import auth_headers, delete_user, make_user


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.company.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_manager(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.company.manager.tmp@example.com",
        role_name="Manager",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.company.bsadmin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def restore_northgate_company(db_session: Session) -> Generator[None, None, None]:
    """Company, unlike every other module's test fixtures, has no throwaway-row option - each
    company has exactly one profile row, and PATCH mutates real seeded demo data (the same
    "the only test fixture that mutates shared seed data" situation Phase 12's
    occupied_unit_id fixture documented). Snapshots every PATCH-able field before the test and
    restores it afterward."""
    company = db_session.query(Company).filter(Company.CompanyName == "Northgate Property Management").one()
    original = {
        "CompanyName": company.CompanyName,
        "AddressLine1": company.AddressLine1,
        "AddressLine2": company.AddressLine2,
        "City": company.City,
        "Postcode": company.Postcode,
        "Telephone": company.Telephone,
        "Email": company.Email,
    }
    yield
    db_session.query(Company).filter(Company.CompanyName == original["CompanyName"]).update(original)
    db_session.commit()


def test_get_company_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/company")
    assert response.status_code == 401


def test_get_company_open_to_manager_role(client: TestClient, northgate_manager) -> None:
    response = client.get("/api/company", headers=auth_headers(client, northgate_manager.Email))
    assert response.status_code == 200
    assert response.json()["CompanyName"] == "Northgate Property Management"


def test_get_company_isolates_by_company(client: TestClient, bright_spaces_admin) -> None:
    response = client.get("/api/company", headers=auth_headers(client, bright_spaces_admin.Email))
    assert response.status_code == 200
    assert response.json()["CompanyName"] == "Bright Spaces Estates"


def test_update_company_as_admin_changes_only_supplied_fields(
    client: TestClient, northgate_admin, restore_northgate_company
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    response = client.patch(
        "/api/company",
        json={"Telephone": "0161 000 1111", "Email": "updated@northgatepm.example"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["Telephone"] == "0161 000 1111"
    assert body["Email"] == "updated@northgatepm.example"
    assert body["CompanyName"] == "Northgate Property Management"  # untouched

    confirm = client.get("/api/company", headers=headers)
    assert confirm.json()["Telephone"] == "0161 000 1111"


def test_update_company_as_manager_returns_403(client: TestClient, northgate_manager) -> None:
    response = client.patch(
        "/api/company",
        json={"Telephone": "0161 000 2222"},
        headers=auth_headers(client, northgate_manager.Email),
    )
    assert response.status_code == 403


def test_update_company_empty_name_returns_422(client: TestClient, northgate_admin) -> None:
    response = client.patch(
        "/api/company",
        json={"CompanyName": ""},
        headers=auth_headers(client, northgate_admin.Email),
    )
    assert response.status_code == 422
