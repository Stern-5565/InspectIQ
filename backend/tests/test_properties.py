"""
Property API tests. Every test hits the real local InspectIQDb (no mocks). Throwaway users are
created via conftest.make_user and cleaned up explicitly; throwaway properties are cleaned up
with a direct DB delete in teardown - a real hard delete is fine for test data even though the
app itself never hard-deletes a Property through its own API (soft-delete-only is an app-layer
design choice, not a DB-level block, unlike InspectionTemplates/Sections/Questions which have a
real trigger preventing it).
"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.property import Property
from tests.conftest import auth_headers, delete_user, make_user


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.properties.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.properties.inspector.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.properties.bsadmin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


def _create_property_payload(**overrides) -> dict:
    payload = {
        "PropertyName": "Test Property TMP",
        "AddressLine1": "1 Test Street",
        "Postcode": "TE5 7ST",
        "PropertyType": "HMO",
        "InspectionFrequency": "Monthly",
    }
    payload.update(overrides)
    return payload


# --- isolation --------------------------------------------------------------------------

def test_list_properties_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/properties")
    assert response.status_code == 401


def test_list_properties_returns_only_own_companys_properties(
    client: TestClient, northgate_admin
) -> None:
    response = client.get("/api/properties", headers=auth_headers(client, northgate_admin.Email))

    assert response.status_code == 200
    body = response.json()
    names = {item["PropertyName"] for item in body["items"]}
    assert "15 High Road" in names
    assert "Riverside Office Suites" not in names  # Bright Spaces' property


def test_get_property_belonging_to_another_company_returns_404_not_403(
    client: TestClient, db_session: Session, northgate_admin, bright_spaces_admin
) -> None:
    """The security-critical isolation case: a Bright Spaces user asking for a Northgate
    property ID must get the same 404 they'd get for a nonexistent ID - not a 403, which
    would confirm something exists there just isn't theirs."""
    from sqlalchemy import select

    northgate_property_id = db_session.execute(
        select(Property.PropertyId).where(Property.PropertyName == "15 High Road")
    ).scalar_one()

    response = client.get(
        f"/api/properties/{northgate_property_id}",
        headers=auth_headers(client, bright_spaces_admin.Email),
    )

    assert response.status_code == 404


# --- authorization ------------------------------------------------------------------------

def test_create_property_as_administrator_succeeds(
    client: TestClient, db_session: Session, northgate_admin
) -> None:
    response = client.post(
        "/api/properties",
        json=_create_property_payload(),
        headers=auth_headers(client, northgate_admin.Email),
    )

    try:
        assert response.status_code == 201
        body = response.json()
        assert body["PropertyName"] == "Test Property TMP"
        assert body["CompanyId"] == northgate_admin.CompanyId
        assert body["IsActive"] is True
    finally:
        db_session.query(Property).filter(Property.PropertyName == "Test Property TMP").delete()
        db_session.commit()


def test_create_property_as_inspector_returns_403(client: TestClient, northgate_inspector) -> None:
    response = client.post(
        "/api/properties",
        json=_create_property_payload(),
        headers=auth_headers(client, northgate_inspector.Email),
    )

    assert response.status_code == 403


def test_create_property_rejects_invalid_property_type(client: TestClient, northgate_admin) -> None:
    response = client.post(
        "/api/properties",
        json=_create_property_payload(PropertyType="NotARealType"),
        headers=auth_headers(client, northgate_admin.Email),
    )

    assert response.status_code == 422


# --- update / deactivate -------------------------------------------------------------------

def test_update_property_changes_only_supplied_fields(
    client: TestClient, db_session: Session, northgate_admin
) -> None:
    create_response = client.post(
        "/api/properties",
        json=_create_property_payload(GeneralNotes="original notes"),
        headers=auth_headers(client, northgate_admin.Email),
    )
    property_id = create_response.json()["PropertyId"]

    try:
        update_response = client.patch(
            f"/api/properties/{property_id}",
            json={"PropertyStatus": "UnderRefurbishment"},
            headers=auth_headers(client, northgate_admin.Email),
        )

        assert update_response.status_code == 200
        body = update_response.json()
        assert body["PropertyStatus"] == "UnderRefurbishment"
        assert body["GeneralNotes"] == "original notes"  # untouched
        assert body["PropertyName"] == "Test Property TMP"  # untouched
    finally:
        db_session.query(Property).filter(Property.PropertyId == property_id).delete()
        db_session.commit()


def test_deactivate_property_hides_it_from_default_list_but_not_direct_lookup(
    client: TestClient, db_session: Session, northgate_admin
) -> None:
    create_response = client.post(
        "/api/properties",
        json=_create_property_payload(),
        headers=auth_headers(client, northgate_admin.Email),
    )
    property_id = create_response.json()["PropertyId"]
    headers = auth_headers(client, northgate_admin.Email)

    try:
        deactivate_response = client.post(f"/api/properties/{property_id}/deactivate", headers=headers)
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["IsActive"] is False

        default_list = client.get("/api/properties", headers=headers).json()
        assert property_id not in [p["PropertyId"] for p in default_list["items"]]

        inactive_included_list = client.get(
            "/api/properties", params={"include_inactive": True}, headers=headers
        ).json()
        assert property_id in [p["PropertyId"] for p in inactive_included_list["items"]]

        direct_lookup = client.get(f"/api/properties/{property_id}", headers=headers)
        assert direct_lookup.status_code == 200
    finally:
        db_session.query(Property).filter(Property.PropertyId == property_id).delete()
        db_session.commit()
