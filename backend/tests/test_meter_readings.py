"""Meter Reading (AI/OCR) API tests - same conventions as test_risk.py (real DB, no mocks,
explicit cleanup)."""
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.inspection import Inspection
from app.models.inspection_response import InspectionResponse
from app.models.inspection_template import InspectionTemplate
from app.models.media_file import MediaFile
from app.models.meter_reading import MeterReading
from app.models.property import Property
from tests.conftest import auth_headers, delete_user, make_user

_FAKE_PHOTO = b"\xff\xd8\xff\xe0fakemeter"


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.meter.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.meter.inspector.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector2(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.meter.inspector2.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_maintenance(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.meter.maintenance.tmp@example.com",
        role_name="Maintenance",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.meter.bsadmin.tmp@example.com",
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


def _delete_reading(db_session: Session, meter_reading_id: int) -> None:
    reading = db_session.get(MeterReading, meter_reading_id)
    if reading is not None and reading.PhotoMediaFileId is not None:
        media = db_session.get(MediaFile, reading.PhotoMediaFileId)
        if media is not None:
            (Path(settings.MEDIA_UPLOAD_DIR) / media.StorageKey).unlink(missing_ok=True)
            db_session.delete(media)
    db_session.query(MeterReading).filter(MeterReading.MeterReadingId == meter_reading_id).delete()
    db_session.commit()


def _create(client: TestClient, headers: dict, property_id: int, **overrides) -> "TestClient":
    data = {"property_id": property_id, "meter_type": "Electricity", **overrides}
    return client.post(
        "/api/meter-readings",
        data=data,
        files={"file": ("meter.jpg", _FAKE_PHOTO, "image/jpeg")},
        headers=headers,
    )


# --- create ------------------------------------------------------------------------------------


def test_create_as_inspector_runs_mock_ocr(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int
) -> None:
    response = _create(
        client,
        auth_headers(client, northgate_inspector.Email),
        northgate_property_id,
        meter_serial_number="MTR-001",
    )

    try:
        assert response.status_code == 201
        body = response.json()
        assert body["PropertyId"] == northgate_property_id
        assert body["MeterType"] == "Electricity"
        assert body["MeterSerialNumber"] == "MTR-001"
        assert body["PhotoMediaFileId"] is not None
        assert body["AIDetectedReading"] == "18294.6000"
        assert body["AIConfidence"] == "0.8700"
        assert body["ConfirmedReading"] is None  # AI value never auto-becomes confirmed
    finally:
        _delete_reading(db_session, response.json()["MeterReadingId"])


def test_create_as_maintenance_role_returns_403(
    client: TestClient, northgate_maintenance, northgate_property_id: int
) -> None:
    response = _create(client, auth_headers(client, northgate_maintenance.Email), northgate_property_id)
    assert response.status_code == 403


def test_create_for_property_in_another_company_returns_404(
    client: TestClient, bright_spaces_admin, northgate_property_id: int
) -> None:
    response = _create(client, auth_headers(client, bright_spaces_admin.Email), northgate_property_id)
    assert response.status_code == 404


def test_create_with_invalid_meter_type_returns_422(
    client: TestClient, northgate_inspector, northgate_property_id: int
) -> None:
    response = _create(
        client, auth_headers(client, northgate_inspector.Email), northgate_property_id, meter_type="Solar"
    )
    assert response.status_code == 422


def test_create_linked_to_inspection_response(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_property_id: int,
    template_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    start = client.post(
        "/api/inspections",
        json={"PropertyId": northgate_property_id, "InspectionTemplateId": template_id},
        headers=headers,
    )
    inspection_id = start.json()["InspectionId"]
    response_id = start.json()["Sections"][0]["Responses"][0]["InspectionResponseId"]

    try:
        response = _create(
            client, headers, northgate_property_id, inspection_response_id=response_id
        )
        assert response.status_code == 201
        assert response.json()["InspectionResponseId"] == response_id
        _delete_reading(db_session, response.json()["MeterReadingId"])
    finally:
        db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection_id).delete()
        db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).delete()
        db_session.commit()


# --- view isolation -------------------------------------------------------------------------


def test_get_meter_reading_in_another_company_returns_404(
    client: TestClient, db_session: Session, northgate_inspector, bright_spaces_admin, northgate_property_id: int
) -> None:
    create = _create(client, auth_headers(client, northgate_inspector.Email), northgate_property_id)
    meter_reading_id = create.json()["MeterReadingId"]

    try:
        response = client.get(
            f"/api/meter-readings/{meter_reading_id}", headers=auth_headers(client, bright_spaces_admin.Email)
        )
        assert response.status_code == 404
    finally:
        _delete_reading(db_session, meter_reading_id)


def test_photo_visible_via_generic_media_endpoint(
    client: TestClient, db_session: Session, northgate_admin, northgate_inspector, northgate_property_id: int
) -> None:
    create = _create(client, auth_headers(client, northgate_inspector.Email), northgate_property_id)
    body = create.json()
    meter_reading_id = body["MeterReadingId"]

    try:
        listing = client.get(
            "/api/media",
            params={"entity_type": "MeterReading", "entity_id": meter_reading_id},
            headers=auth_headers(client, northgate_admin.Email),
        )
        assert listing.status_code == 200
        assert listing.json()["total"] == 1
        assert listing.json()["items"][0]["MediaFileId"] == body["PhotoMediaFileId"]
    finally:
        _delete_reading(db_session, meter_reading_id)


# --- confirm / update (hybrid authorization tier) -------------------------------------------


def test_confirm_inspection_linked_reading_by_assigned_inspector_succeeds(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_property_id: int,
    template_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    start = client.post(
        "/api/inspections",
        json={"PropertyId": northgate_property_id, "InspectionTemplateId": template_id},
        headers=headers,
    )
    inspection_id = start.json()["InspectionId"]
    response_id = start.json()["Sections"][0]["Responses"][0]["InspectionResponseId"]

    try:
        create = _create(client, headers, northgate_property_id, inspection_response_id=response_id)
        meter_reading_id = create.json()["MeterReadingId"]

        response = client.patch(
            f"/api/meter-readings/{meter_reading_id}",
            json={"ConfirmedReading": "18300.0"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["ConfirmedReading"] == "18300.0000"
        _delete_reading(db_session, meter_reading_id)
    finally:
        db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection_id).delete()
        db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).delete()
        db_session.commit()


def test_confirm_inspection_linked_reading_by_unassigned_inspector_returns_403(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_inspector2,
    northgate_property_id: int,
    template_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    start = client.post(
        "/api/inspections",
        json={"PropertyId": northgate_property_id, "InspectionTemplateId": template_id},
        headers=headers,
    )
    inspection_id = start.json()["InspectionId"]
    response_id = start.json()["Sections"][0]["Responses"][0]["InspectionResponseId"]

    try:
        create = _create(client, headers, northgate_property_id, inspection_response_id=response_id)
        meter_reading_id = create.json()["MeterReadingId"]

        response = client.patch(
            f"/api/meter-readings/{meter_reading_id}",
            json={"ConfirmedReading": "18300.0"},
            headers=auth_headers(client, northgate_inspector2.Email),
        )
        assert response.status_code == 403
        _delete_reading(db_session, meter_reading_id)
    finally:
        db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection_id).delete()
        db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).delete()
        db_session.commit()


def test_confirm_standalone_reading_as_inspector_returns_403_but_admin_succeeds(
    client: TestClient, db_session: Session, northgate_admin, northgate_inspector, northgate_property_id: int
) -> None:
    create = _create(client, auth_headers(client, northgate_inspector.Email), northgate_property_id)
    meter_reading_id = create.json()["MeterReadingId"]

    try:
        forbidden = client.patch(
            f"/api/meter-readings/{meter_reading_id}",
            json={"ConfirmedReading": "18300.0"},
            headers=auth_headers(client, northgate_inspector.Email),
        )
        assert forbidden.status_code == 403

        response = client.patch(
            f"/api/meter-readings/{meter_reading_id}",
            json={"ConfirmedReading": "18300.0"},
            headers=auth_headers(client, northgate_admin.Email),
        )
        assert response.status_code == 200
        assert response.json()["ConfirmedReading"] == "18300.0000"
    finally:
        _delete_reading(db_session, meter_reading_id)


def test_list_meter_readings(
    client: TestClient, db_session: Session, northgate_admin, northgate_inspector, northgate_property_id: int
) -> None:
    create = _create(client, auth_headers(client, northgate_inspector.Email), northgate_property_id)
    meter_reading_id = create.json()["MeterReadingId"]

    try:
        response = client.get(
            "/api/meter-readings",
            params={"property_id": northgate_property_id},
            headers=auth_headers(client, northgate_admin.Email),
        )
        assert response.status_code == 200
        assert meter_reading_id in [r["MeterReadingId"] for r in response.json()["items"]]
    finally:
        _delete_reading(db_session, meter_reading_id)


def test_list_filtered_by_inspection_response_id(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_property_id: int,
    template_id: int,
) -> None:
    """Sub-phase D's own need (app/api/meter_readings.py's module docstring): the wizard's
    Question screen must be able to ask "does a reading already exist for THIS response" without
    fetching every reading at the property."""
    headers = auth_headers(client, northgate_inspector.Email)
    start = client.post(
        "/api/inspections",
        json={"PropertyId": northgate_property_id, "InspectionTemplateId": template_id},
        headers=headers,
    )
    inspection_id = start.json()["InspectionId"]
    responses = start.json()["Sections"][0]["Responses"]
    linked_response_id = responses[0]["InspectionResponseId"]
    other_response_id = responses[1]["InspectionResponseId"]

    try:
        create = _create(client, headers, northgate_property_id, inspection_response_id=linked_response_id)
        meter_reading_id = create.json()["MeterReadingId"]

        matched = client.get(
            "/api/meter-readings", params={"inspection_response_id": linked_response_id}, headers=headers
        )
        assert matched.status_code == 200
        assert [r["MeterReadingId"] for r in matched.json()["items"]] == [meter_reading_id]

        unmatched = client.get(
            "/api/meter-readings", params={"inspection_response_id": other_response_id}, headers=headers
        )
        assert unmatched.status_code == 200
        assert unmatched.json()["items"] == []

        _delete_reading(db_session, meter_reading_id)
    finally:
        db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection_id).delete()
        db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).delete()
        db_session.commit()
