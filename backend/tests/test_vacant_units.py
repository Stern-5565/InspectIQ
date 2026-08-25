"""Vacant Unit Inspection API tests - same conventions as test_cleaning.py (real DB, no mocks,
explicit cleanup)."""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.inspection_response import InspectionResponse
from app.models.inspection_template import InspectionTemplate
from app.models.media_file import MediaFile
from app.models.property import Property
from app.models.unit import Unit
from app.models.vacant_unit_inspection import VacantUnitInspection
from tests.conftest import auth_headers, delete_user, make_user


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.vacant.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.vacant.inspector.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector2(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.vacant.inspector2.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.vacant.bsadmin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_property_id(db_session: Session) -> int:
    return db_session.execute(
        select(Property.PropertyId).where(Property.PropertyName == "15 High Road")
    ).scalar_one()


@pytest.fixture
def template_id(db_session: Session) -> int:
    return db_session.execute(
        select(InspectionTemplate.InspectionTemplateId).where(
            InspectionTemplate.TemplateName == "Monthly Property Inspection"
        )
    ).scalar_one()


@pytest.fixture
def occupied_unit_id(db_session: Session, northgate_property_id: int) -> Generator[int, None, None]:
    """A real, currently-Occupied demo unit ("Flat 1") - reused rather than created, so the
    auto-vacant-on-create side effect (app/services/vacant_unit_service.py) has something real
    to flip. Restored to Occupied in teardown - this test deliberately mutates seeded demo data,
    unlike every other fixture in this file, which only adds/removes its own throwaway rows."""
    unit_id = db_session.execute(
        select(Unit.UnitId).where(Unit.PropertyId == northgate_property_id, Unit.UnitNumber == "Flat 1")
    ).scalar_one()
    yield unit_id
    db_session.query(Unit).filter(Unit.UnitId == unit_id).update({"OccupancyStatus": "Occupied"})
    db_session.commit()


def _delete_inspection(db_session: Session, inspection_id: int) -> None:
    db_session.query(VacantUnitInspection).filter(
        VacantUnitInspection.InspectionId == inspection_id
    ).delete()
    db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection_id).delete()
    db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).delete()
    db_session.commit()


def _start_inspection(client: TestClient, headers: dict, property_id: int, template_id: int) -> dict:
    response = client.post(
        "/api/inspections",
        json={"PropertyId": property_id, "InspectionTemplateId": template_id},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


# --- create ------------------------------------------------------------------------------------


def test_create_as_assigned_inspector_marks_unit_vacant(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_property_id: int,
    template_id: int,
    occupied_unit_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        response = client.post(
            f"/api/inspections/{inspection_id}/vacant-unit-inspections",
            json={
                "UnitId": occupied_unit_id,
                "Condition": "Fair",
                "ElectricityOn": False,
                "SignsOfDamp": True,
                "MaintenanceRequired": True,
            },
            headers=headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["UnitId"] == occupied_unit_id
        assert body["Condition"] == "Fair"
        assert body["ElectricityOn"] is False
        assert body["SignsOfDamp"] is True
        assert body["WaterOn"] is None  # never supplied - stays a genuine unknown, not False
        assert body["DateIdentifiedVacant"] is not None

        # An Inspector isn't normally allowed to change occupancy directly (that standalone
        # endpoint is Admin/Manager only, app/api/units.py) - but recording a vacant-unit
        # finding as part of conducting THIS inspection is exactly the sanctioned exception
        # documented in app/services/vacant_unit_service.py.
        unit_check = client.get(f"/api/units/{occupied_unit_id}", headers=headers)
        assert unit_check.json()["OccupancyStatus"] == "Vacant"
    finally:
        _delete_inspection(db_session, inspection_id)


def test_create_with_unit_from_another_property_returns_422(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_property_id: int,
    template_id: int,
) -> None:
    northgate_company_id = db_session.execute(
        select(Property.CompanyId).where(Property.PropertyId == northgate_property_id)
    ).scalar_one()
    other_property_id = db_session.execute(
        select(Property.PropertyId).where(
            Property.PropertyId != northgate_property_id, Property.CompanyId == northgate_company_id
        )
    ).scalars().first()
    other_unit_id = db_session.execute(
        select(Unit.UnitId).where(Unit.PropertyId == other_property_id)
    ).scalars().first()

    headers = auth_headers(client, northgate_inspector.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        response = client.post(
            f"/api/inspections/{inspection_id}/vacant-unit-inspections",
            json={"UnitId": other_unit_id},
            headers=headers,
        )
        assert response.status_code == 422
    finally:
        _delete_inspection(db_session, inspection_id)


def test_create_by_unassigned_inspector_returns_403(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_inspector2,
    northgate_property_id: int,
    template_id: int,
    occupied_unit_id: int,
) -> None:
    inspection = _start_inspection(
        client, auth_headers(client, northgate_inspector.Email), northgate_property_id, template_id
    )
    inspection_id = inspection["InspectionId"]

    try:
        response = client.post(
            f"/api/inspections/{inspection_id}/vacant-unit-inspections",
            json={"UnitId": occupied_unit_id},
            headers=auth_headers(client, northgate_inspector2.Email),
        )
        assert response.status_code == 403
    finally:
        _delete_inspection(db_session, inspection_id)


def test_create_on_submitted_inspection_returns_409(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    northgate_property_id: int,
    template_id: int,
    occupied_unit_id: int,
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).update(
            {"Status": "Submitted"}
        )
        db_session.commit()

        response = client.post(
            f"/api/inspections/{inspection_id}/vacant-unit-inspections",
            json={"UnitId": occupied_unit_id},
            headers=headers,
        )
        assert response.status_code == 409
    finally:
        _delete_inspection(db_session, inspection_id)


# --- view isolation ------------------------------------------------------------------------

def test_list_for_inspection_in_another_company_returns_404(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    bright_spaces_admin,
    northgate_property_id: int,
    template_id: int,
    occupied_unit_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        client.post(
            f"/api/inspections/{inspection_id}/vacant-unit-inspections",
            json={"UnitId": occupied_unit_id},
            headers=headers,
        )
        response = client.get(
            f"/api/inspections/{inspection_id}/vacant-unit-inspections",
            headers=auth_headers(client, bright_spaces_admin.Email),
        )
        assert response.status_code == 404
    finally:
        _delete_inspection(db_session, inspection_id)


# --- update ------------------------------------------------------------------------------------


def test_update_changes_only_supplied_fields(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_property_id: int,
    template_id: int,
    occupied_unit_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        create = client.post(
            f"/api/inspections/{inspection_id}/vacant-unit-inspections",
            json={"UnitId": occupied_unit_id, "Condition": "Poor", "WaterOn": True},
            headers=headers,
        )
        record_id = create.json()["VacantUnitInspectionId"]

        update = client.patch(
            f"/api/vacant-unit-inspections/{record_id}",
            json={"Notes": "Follow-up scheduled"},
            headers=headers,
        )
        assert update.status_code == 200
        body = update.json()
        assert body["Notes"] == "Follow-up scheduled"
        assert body["Condition"] == "Poor"  # untouched
        assert body["WaterOn"] is True  # untouched

        listing = client.get(
            f"/api/inspections/{inspection_id}/vacant-unit-inspections", headers=headers
        )
        assert len(listing.json()) == 1
        assert listing.json()[0]["VacantUnitInspectionId"] == record_id
    finally:
        _delete_inspection(db_session, inspection_id)


def test_upload_photo_to_vacant_unit_inspection_via_media_endpoint(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_property_id: int,
    template_id: int,
    occupied_unit_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        create = client.post(
            f"/api/inspections/{inspection_id}/vacant-unit-inspections",
            json={"UnitId": occupied_unit_id},
            headers=headers,
        )
        record_id = create.json()["VacantUnitInspectionId"]

        upload = client.post(
            "/api/media",
            data={"entity_type": "VacantUnitInspection", "entity_id": record_id},
            files={"file": ("empty_unit.jpg", b"\xff\xd8\xff\xe0fake", "image/jpeg")},
            headers=headers,
        )
        assert upload.status_code == 201
        media_file_id = upload.json()["MediaFileId"]

        listing = client.get(
            "/api/media",
            params={"entity_type": "VacantUnitInspection", "entity_id": record_id},
            headers=headers,
        )
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

        media = db_session.get(MediaFile, media_file_id)
        from pathlib import Path

        from app.core.config import settings

        (Path(settings.MEDIA_UPLOAD_DIR) / media.StorageKey).unlink(missing_ok=True)
        db_session.delete(media)
        db_session.commit()
    finally:
        _delete_inspection(db_session, inspection_id)


# --- Standalone Vacant Units module: GET /vacant-unit-inspections (list) and .../{id} (detail) --


def test_list_all_vacant_unit_inspections_includes_property_and_unit_number(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    northgate_property_id: int,
    template_id: int,
    occupied_unit_id: int,
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        create = client.post(
            f"/api/inspections/{inspection_id}/vacant-unit-inspections",
            json={"UnitId": occupied_unit_id, "Condition": "Fair"},
            headers=headers,
        )
        assert create.status_code == 201
        record_id = create.json()["VacantUnitInspectionId"]

        listing = client.get("/api/vacant-unit-inspections", headers=headers)
        assert listing.status_code == 200
        matches = [i for i in listing.json()["items"] if i["VacantUnitInspectionId"] == record_id]
        assert len(matches) == 1
        assert matches[0]["PropertyId"] == northgate_property_id
        assert matches[0]["UnitNumber"] == "Flat 1"
        assert matches[0]["Condition"] == "Fair"

        filtered = client.get(
            "/api/vacant-unit-inspections", params={"property_id": northgate_property_id}, headers=headers
        )
        assert filtered.status_code == 200
        assert record_id in [i["VacantUnitInspectionId"] for i in filtered.json()["items"]]

        other_property_id = db_session.execute(
            select(Property.PropertyId).where(
                Property.PropertyId != northgate_property_id,
                Property.CompanyId
                == db_session.execute(
                    select(Property.CompanyId).where(Property.PropertyId == northgate_property_id)
                ).scalar_one(),
            )
        ).scalars().first()
        filtered_out = client.get(
            "/api/vacant-unit-inspections", params={"property_id": other_property_id}, headers=headers
        )
        assert filtered_out.status_code == 200
        assert record_id not in [i["VacantUnitInspectionId"] for i in filtered_out.json()["items"]]
    finally:
        _delete_inspection(db_session, inspection_id)


def test_get_vacant_unit_inspection_detail_isolates_by_company(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    bright_spaces_admin,
    northgate_property_id: int,
    template_id: int,
    occupied_unit_id: int,
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        create = client.post(
            f"/api/inspections/{inspection_id}/vacant-unit-inspections",
            json={"UnitId": occupied_unit_id},
            headers=headers,
        )
        record_id = create.json()["VacantUnitInspectionId"]

        own_view = client.get(f"/api/vacant-unit-inspections/{record_id}", headers=headers)
        assert own_view.status_code == 200
        assert own_view.json()["UnitNumber"] == "Flat 1"
        assert own_view.json()["PropertyId"] == northgate_property_id

        other_view = client.get(
            f"/api/vacant-unit-inspections/{record_id}",
            headers=auth_headers(client, bright_spaces_admin.Email),
        )
        assert other_view.status_code == 404
    finally:
        _delete_inspection(db_session, inspection_id)
