"""Communal Cleaning Grading API tests - same conventions as test_maintenance.py (real DB, no
mocks, explicit cleanup)."""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cleaning_area import CleaningArea
from app.models.cleaning_inspection import CleaningInspection
from app.models.inspection import Inspection
from app.models.inspection_response import InspectionResponse
from app.models.inspection_template import InspectionTemplate
from app.models.media_file import MediaFile
from app.models.property import Property
from tests.conftest import auth_headers, delete_user, make_user


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.cleaning.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.cleaning.inspector.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector2(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.cleaning.inspector2.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.cleaning.bsadmin.tmp@example.com",
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
def northgate_area_id(db_session: Session, northgate_property_id: int) -> Generator[int, None, None]:
    # "15 High Road" is an HMO with no seeded communal areas of its own (only "Elm Court", a
    # block of flats, got demo CleaningAreas in database/seed/13_SeedSampleData.sql) - and
    # Phase 11's auto-seed-on-create only applies to properties created AFTER this phase, not
    # this pre-existing seeded one. A real throwaway area is more robust than depending on
    # which demo property happens to have pre-seeded ones.
    area = CleaningArea(PropertyId=northgate_property_id, AreaName="Test Area TMP", AreaType="Entrance")
    db_session.add(area)
    db_session.commit()
    db_session.refresh(area)
    yield area.CleaningAreaId
    db_session.query(CleaningArea).filter(CleaningArea.CleaningAreaId == area.CleaningAreaId).delete()
    db_session.commit()


def _delete_inspection(db_session: Session, inspection_id: int) -> None:
    db_session.query(CleaningInspection).filter(CleaningInspection.InspectionId == inspection_id).delete()
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


# --- CleaningAreas ---------------------------------------------------------------------------


def test_new_property_auto_seeds_three_default_cleaning_areas(
    client: TestClient, db_session: Session, northgate_admin
) -> None:
    create = client.post(
        "/api/properties",
        json={
            "PropertyName": "Cleaning Test Property TMP",
            "AddressLine1": "1 Test Street",
            "Postcode": "TE5 7ST",
            "PropertyType": "HMO",
            "InspectionFrequency": "Monthly",
        },
        headers=auth_headers(client, northgate_admin.Email),
    )
    property_id = create.json()["PropertyId"]

    try:
        response = client.get(
            f"/api/properties/{property_id}/cleaning-areas", headers=auth_headers(client, northgate_admin.Email)
        )
        assert response.status_code == 200
        areas = response.json()
        assert len(areas) == 3
        assert {a["AreaType"] for a in areas} == {"Entrance", "Hallway", "BinArea"}
        assert all(a["IsActive"] for a in areas)
    finally:
        db_session.query(CleaningArea).filter(CleaningArea.PropertyId == property_id).delete()
        db_session.query(Property).filter(Property.PropertyId == property_id).delete()
        db_session.commit()


def test_create_area_as_admin_succeeds(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    response = client.post(
        f"/api/properties/{northgate_property_id}/cleaning-areas",
        json={"AreaName": "Roof Terrace TMP", "AreaType": "Other"},
        headers=auth_headers(client, northgate_admin.Email),
    )

    try:
        assert response.status_code == 201
        assert response.json()["AreaName"] == "Roof Terrace TMP"
    finally:
        db_session.query(CleaningArea).filter(CleaningArea.AreaName == "Roof Terrace TMP").delete()
        db_session.commit()


def test_create_area_as_inspector_returns_403(
    client: TestClient, northgate_inspector, northgate_property_id: int
) -> None:
    response = client.post(
        f"/api/properties/{northgate_property_id}/cleaning-areas",
        json={"AreaName": "Should Not Exist TMP", "AreaType": "Other"},
        headers=auth_headers(client, northgate_inspector.Email),
    )
    assert response.status_code == 403


def test_create_area_for_property_in_another_company_returns_404(
    client: TestClient, bright_spaces_admin, northgate_property_id: int
) -> None:
    response = client.post(
        f"/api/properties/{northgate_property_id}/cleaning-areas",
        json={"AreaName": "Should Not Exist TMP", "AreaType": "Other"},
        headers=auth_headers(client, bright_spaces_admin.Email),
    )
    assert response.status_code == 404


def test_update_area_rename_and_deactivate(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    create = client.post(
        f"/api/properties/{northgate_property_id}/cleaning-areas",
        json={"AreaName": "Laundry TMP", "AreaType": "LaundryArea"},
        headers=auth_headers(client, northgate_admin.Email),
    )
    area_id = create.json()["CleaningAreaId"]

    try:
        response = client.patch(
            f"/api/cleaning-areas/{area_id}",
            json={"AreaName": "Laundry Room TMP", "IsActive": False},
            headers=auth_headers(client, northgate_admin.Email),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["AreaName"] == "Laundry Room TMP"
        assert body["IsActive"] is False

        default_list = client.get(
            f"/api/properties/{northgate_property_id}/cleaning-areas",
            headers=auth_headers(client, northgate_admin.Email),
        ).json()
        assert area_id not in [a["CleaningAreaId"] for a in default_list]

        with_inactive = client.get(
            f"/api/properties/{northgate_property_id}/cleaning-areas",
            params={"include_inactive": True},
            headers=auth_headers(client, northgate_admin.Email),
        ).json()
        assert area_id in [a["CleaningAreaId"] for a in with_inactive]
    finally:
        db_session.query(CleaningArea).filter(CleaningArea.CleaningAreaId == area_id).delete()
        db_session.commit()


# --- CleaningInspections (grading) ------------------------------------------------------------


def test_create_grade_as_assigned_inspector_succeeds(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_property_id: int,
    template_id: int,
    northgate_area_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        response = client.post(
            f"/api/inspections/{inspection_id}/cleaning",
            json={"CleaningAreaId": northgate_area_id, "Grade": "B", "CleaningRequired": True},
            headers=headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["Grade"] == "B"
        assert body["Status"] == "Pending"
        assert body["CleaningRequired"] is True
    finally:
        _delete_inspection(db_session, inspection_id)


def test_create_grade_with_assigned_user_starts_status_assigned(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_admin,
    northgate_property_id: int,
    template_id: int,
    northgate_area_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        response = client.post(
            f"/api/inspections/{inspection_id}/cleaning",
            json={
                "CleaningAreaId": northgate_area_id,
                "Grade": "D",
                "Urgent": True,
                "AssignedUserId": northgate_admin.UserId,
            },
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["Status"] == "Assigned"
        assert response.json()["AssignedUserId"] == northgate_admin.UserId
    finally:
        _delete_inspection(db_session, inspection_id)


def test_create_grade_with_area_from_another_property_returns_422(
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
    other_area_id = db_session.execute(
        select(CleaningArea.CleaningAreaId).where(CleaningArea.PropertyId == other_property_id)
    ).scalars().first()

    headers = auth_headers(client, northgate_inspector.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        response = client.post(
            f"/api/inspections/{inspection_id}/cleaning",
            json={"CleaningAreaId": other_area_id, "Grade": "A"},
            headers=headers,
        )
        assert response.status_code == 422
    finally:
        _delete_inspection(db_session, inspection_id)


def test_create_grade_by_unassigned_inspector_returns_403(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_inspector2,
    northgate_property_id: int,
    template_id: int,
    northgate_area_id: int,
) -> None:
    inspection = _start_inspection(
        client, auth_headers(client, northgate_inspector.Email), northgate_property_id, template_id
    )
    inspection_id = inspection["InspectionId"]

    try:
        response = client.post(
            f"/api/inspections/{inspection_id}/cleaning",
            json={"CleaningAreaId": northgate_area_id, "Grade": "C"},
            headers=auth_headers(client, northgate_inspector2.Email),
        )
        assert response.status_code == 403
    finally:
        _delete_inspection(db_session, inspection_id)


def test_create_grade_on_submitted_inspection_returns_409(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    northgate_property_id: int,
    template_id: int,
    northgate_area_id: int,
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        # Force-submit directly at the DB layer (mandatory checklist questions aren't answered -
        # not what this test is about) rather than fighting Phase 8's submission gating just to
        # reach a Submitted inspection.
        db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).update(
            {"Status": "Submitted"}
        )
        db_session.commit()

        response = client.post(
            f"/api/inspections/{inspection_id}/cleaning",
            json={"CleaningAreaId": northgate_area_id, "Grade": "A"},
            headers=headers,
        )
        assert response.status_code == 409
    finally:
        _delete_inspection(db_session, inspection_id)


def test_update_grade_and_list_timeline_order(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_property_id: int,
    template_id: int,
    northgate_area_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        create = client.post(
            f"/api/inspections/{inspection_id}/cleaning",
            json={"CleaningAreaId": northgate_area_id, "Grade": "E", "Urgent": True},
            headers=headers,
        )
        cleaning_inspection_id = create.json()["CleaningInspectionId"]

        update = client.patch(
            f"/api/cleaning-inspections/{cleaning_inspection_id}",
            json={"Status": "Completed", "Notes": "Deep cleaned"},
            headers=headers,
        )
        assert update.status_code == 200
        assert update.json()["Status"] == "Completed"
        assert update.json()["Notes"] == "Deep cleaned"
        assert update.json()["Grade"] == "E"  # untouched by the partial update

        listing = client.get(f"/api/inspections/{inspection_id}/cleaning", headers=headers)
        assert listing.status_code == 200
        assert len(listing.json()) == 1
        assert listing.json()[0]["CleaningInspectionId"] == cleaning_inspection_id
    finally:
        _delete_inspection(db_session, inspection_id)


def test_upload_photo_to_cleaning_inspection_via_media_endpoint(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_property_id: int,
    template_id: int,
    northgate_area_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        create = client.post(
            f"/api/inspections/{inspection_id}/cleaning",
            json={"CleaningAreaId": northgate_area_id, "Grade": "C"},
            headers=headers,
        )
        cleaning_inspection_id = create.json()["CleaningInspectionId"]

        upload = client.post(
            "/api/media",
            data={"entity_type": "CleaningInspection", "entity_id": cleaning_inspection_id},
            files={"file": ("bin_area.jpg", b"\xff\xd8\xff\xe0fake", "image/jpeg")},
            headers=headers,
        )
        assert upload.status_code == 201
        media_file_id = upload.json()["MediaFileId"]

        listing = client.get(
            "/api/media",
            params={"entity_type": "CleaningInspection", "entity_id": cleaning_inspection_id},
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


# --- Standalone Cleaning module: GET /cleaning-inspections (list) and .../{id} (detail) --------


def test_list_all_cleaning_inspections_includes_property_and_area_name(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    northgate_property_id: int,
    northgate_area_id: int,
    template_id: int,
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        create = client.post(
            f"/api/inspections/{inspection_id}/cleaning",
            json={"CleaningAreaId": northgate_area_id, "Grade": "C"},
            headers=headers,
        )
        assert create.status_code == 201
        cleaning_inspection_id = create.json()["CleaningInspectionId"]

        listing = client.get("/api/cleaning-inspections", headers=headers)
        assert listing.status_code == 200
        matches = [i for i in listing.json()["items"] if i["CleaningInspectionId"] == cleaning_inspection_id]
        assert len(matches) == 1
        assert matches[0]["PropertyId"] == northgate_property_id
        assert matches[0]["AreaName"] == "Test Area TMP"
        assert matches[0]["Grade"] == "C"

        filtered = client.get(
            "/api/cleaning-inspections", params={"grade": "C", "property_id": northgate_property_id}, headers=headers
        )
        assert filtered.status_code == 200
        assert cleaning_inspection_id in [i["CleaningInspectionId"] for i in filtered.json()["items"]]

        filtered_out = client.get("/api/cleaning-inspections", params={"grade": "A"}, headers=headers)
        assert filtered_out.status_code == 200
        assert cleaning_inspection_id not in [i["CleaningInspectionId"] for i in filtered_out.json()["items"]]
    finally:
        _delete_inspection(db_session, inspection_id)


def test_get_cleaning_inspection_detail_isolates_by_company(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    bright_spaces_admin,
    northgate_property_id: int,
    northgate_area_id: int,
    template_id: int,
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    inspection = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = inspection["InspectionId"]

    try:
        create = client.post(
            f"/api/inspections/{inspection_id}/cleaning",
            json={"CleaningAreaId": northgate_area_id, "Grade": "B"},
            headers=headers,
        )
        cleaning_inspection_id = create.json()["CleaningInspectionId"]

        own_view = client.get(f"/api/cleaning-inspections/{cleaning_inspection_id}", headers=headers)
        assert own_view.status_code == 200
        assert own_view.json()["AreaName"] == "Test Area TMP"
        assert own_view.json()["PropertyId"] == northgate_property_id

        other_view = client.get(
            f"/api/cleaning-inspections/{cleaning_inspection_id}",
            headers=auth_headers(client, bright_spaces_admin.Email),
        )
        assert other_view.status_code == 404
    finally:
        _delete_inspection(db_session, inspection_id)
