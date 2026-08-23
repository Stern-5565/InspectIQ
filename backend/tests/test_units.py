"""Unit API tests - same conventions as test_properties.py (real DB, no mocks, explicit cleanup)."""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.unit import Unit
from tests.conftest import auth_headers, delete_user, make_user


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.units.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.units.inspector.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.units.bsadmin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_property_id(db_session: Session) -> int:
    return db_session.execute(
        select(Property.PropertyId).where(Property.PropertyName == "15 High Road")
    ).scalar_one()


def test_list_units_for_a_property_in_another_company_returns_404(
    client: TestClient, bright_spaces_admin, northgate_property_id: int
) -> None:
    response = client.get(
        f"/api/properties/{northgate_property_id}/units",
        headers=auth_headers(client, bright_spaces_admin.Email),
    )
    assert response.status_code == 404


def test_create_unit_as_administrator_succeeds(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    response = client.post(
        f"/api/properties/{northgate_property_id}/units",
        json={"UnitNumber": "Test Unit TMP", "OccupancyStatus": "Vacant"},
        headers=auth_headers(client, northgate_admin.Email),
    )

    try:
        assert response.status_code == 201
        body = response.json()
        assert body["UnitNumber"] == "Test Unit TMP"
        assert body["PropertyId"] == northgate_property_id
        assert body["OccupancyStatus"] == "Vacant"
    finally:
        db_session.query(Unit).filter(Unit.UnitNumber == "Test Unit TMP").delete()
        db_session.commit()


def test_create_unit_as_inspector_returns_403(
    client: TestClient, northgate_inspector, northgate_property_id: int
) -> None:
    response = client.post(
        f"/api/properties/{northgate_property_id}/units",
        json={"UnitNumber": "Test Unit TMP", "OccupancyStatus": "Vacant"},
        headers=auth_headers(client, northgate_inspector.Email),
    )
    assert response.status_code == 403


def test_create_unit_under_another_companys_property_returns_404(
    client: TestClient, bright_spaces_admin, northgate_property_id: int
) -> None:
    """A Bright Spaces admin can create units for their own properties, but must not be able
    to attach one to a Northgate property just by guessing its PropertyId."""
    response = client.post(
        f"/api/properties/{northgate_property_id}/units",
        json={"UnitNumber": "Should Not Exist TMP", "OccupancyStatus": "Vacant"},
        headers=auth_headers(client, bright_spaces_admin.Email),
    )
    assert response.status_code == 404


def test_get_unit_belonging_to_another_company_returns_404(
    client: TestClient, db_session: Session, northgate_admin, bright_spaces_admin, northgate_property_id: int
) -> None:
    create_response = client.post(
        f"/api/properties/{northgate_property_id}/units",
        json={"UnitNumber": "Test Unit TMP2", "OccupancyStatus": "Vacant"},
        headers=auth_headers(client, northgate_admin.Email),
    )
    unit_id = create_response.json()["UnitId"]

    try:
        response = client.get(
            f"/api/units/{unit_id}", headers=auth_headers(client, bright_spaces_admin.Email)
        )
        assert response.status_code == 404
    finally:
        db_session.query(Unit).filter(Unit.UnitId == unit_id).delete()
        db_session.commit()


def test_update_unit_occupancy_dedicated_endpoint(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    create_response = client.post(
        f"/api/properties/{northgate_property_id}/units",
        json={"UnitNumber": "Test Unit TMP3", "OccupancyStatus": "Occupied"},
        headers=auth_headers(client, northgate_admin.Email),
    )
    unit_id = create_response.json()["UnitId"]
    headers = auth_headers(client, northgate_admin.Email)

    try:
        response = client.patch(
            f"/api/units/{unit_id}/occupancy", json={"OccupancyStatus": "Vacant"}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["OccupancyStatus"] == "Vacant"

        # General PATCH must not accept an OccupancyStatus field - it's not part of that
        # schema, so this proves it's silently ignored rather than applied.
        general_update = client.patch(
            f"/api/units/{unit_id}",
            json={"Notes": "updated via general patch", "OccupancyStatus": "Occupied"},
            headers=headers,
        )
        assert general_update.status_code == 200
        assert general_update.json()["OccupancyStatus"] == "Vacant"  # unchanged
        assert general_update.json()["Notes"] == "updated via general patch"
    finally:
        db_session.query(Unit).filter(Unit.UnitId == unit_id).delete()
        db_session.commit()
