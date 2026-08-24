"""Maintenance Issue API tests - same conventions as test_inspections.py (real DB, no mocks,
explicit cleanup, including MaintenanceUpdates rows and any file written to backend/uploads/)."""
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
from app.models.maintenance_issue import MaintenanceIssue
from app.models.maintenance_update import MaintenanceUpdate
from app.models.media_file import MediaFile
from app.models.property import Property
from tests.conftest import auth_headers, delete_user, make_user


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.maint.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_manager(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.maint.manager.tmp@example.com",
        role_name="Manager",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.maint.inspector.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_maintenance(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.maint.worker.tmp@example.com",
        role_name="Maintenance",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_maintenance2(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.maint.worker2.tmp@example.com",
        role_name="Maintenance",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.maint.bsadmin.tmp@example.com",
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


def _delete_issue(db_session: Session, issue_id: int) -> None:
    media = db_session.execute(
        select(MediaFile).where(MediaFile.EntityType == "MaintenanceIssue", MediaFile.EntityId == issue_id)
    ).scalars().all()
    for m in media:
        (Path(settings.MEDIA_UPLOAD_DIR) / m.StorageKey).unlink(missing_ok=True)
        db_session.delete(m)
    db_session.query(MaintenanceUpdate).filter(MaintenanceUpdate.MaintenanceIssueId == issue_id).delete()
    db_session.query(MaintenanceIssue).filter(MaintenanceIssue.MaintenanceIssueId == issue_id).delete()
    db_session.commit()


def _create(client: TestClient, headers: dict, **overrides) -> "TestClient":
    payload = {"Title": "Leaking tap", "Category": "Plumbing", "Priority": "Medium", **overrides}
    return client.post("/api/maintenance-issues", json=payload, headers=headers)


# --- create -----------------------------------------------------------------------------

def test_create_manual_issue_as_inspector_succeeds(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    response = _create(client, headers, PropertyId=northgate_property_id)

    try:
        assert response.status_code == 201
        body = response.json()
        assert body["Status"] == "Open"
        assert body["PropertyId"] == northgate_property_id
        assert body["ReportedByUserId"] == northgate_inspector.UserId
        assert len(body["Updates"]) == 1
        assert body["Updates"][0]["UpdateType"] == "StatusChange"
        assert body["Updates"][0]["NewStatus"] == "Open"
    finally:
        _delete_issue(db_session, response.json()["MaintenanceIssueId"])


def test_create_issue_as_maintenance_role_returns_403(
    client: TestClient, northgate_maintenance, northgate_property_id: int
) -> None:
    response = _create(client, auth_headers(client, northgate_maintenance.Email), PropertyId=northgate_property_id)
    assert response.status_code == 403


def test_create_issue_for_property_in_another_company_returns_404(
    client: TestClient, bright_spaces_admin, northgate_property_id: int
) -> None:
    response = _create(client, auth_headers(client, bright_spaces_admin.Email), PropertyId=northgate_property_id)
    assert response.status_code == 404


def test_create_issue_without_property_or_inspection_returns_422(
    client: TestClient, northgate_inspector
) -> None:
    response = _create(client, auth_headers(client, northgate_inspector.Email))
    assert response.status_code == 422


def test_create_issue_with_assigned_user_starts_status_assigned(
    client: TestClient, db_session: Session, northgate_admin, northgate_maintenance, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    response = _create(
        client, headers, PropertyId=northgate_property_id, AssignedUserId=northgate_maintenance.UserId
    )

    try:
        assert response.status_code == 201
        body = response.json()
        assert body["Status"] == "Assigned"
        assert body["AssignedUserId"] == northgate_maintenance.UserId
    finally:
        _delete_issue(db_session, response.json()["MaintenanceIssueId"])


def test_create_issue_from_inspection_response_derives_property_and_location(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_property_id: int,
    template_id: int,
) -> None:
    inspector_headers = auth_headers(client, northgate_inspector.Email)
    start = client.post(
        "/api/inspections",
        json={"PropertyId": northgate_property_id, "InspectionTemplateId": template_id},
        headers=inspector_headers,
    )
    inspection_body = start.json()
    inspection_id = inspection_body["InspectionId"]
    first_response = inspection_body["Sections"][0]["Responses"][0]
    response_id = first_response["InspectionResponseId"]

    try:
        response = _create(client, inspector_headers, InspectionResponseId=response_id)
        assert response.status_code == 201
        body = response.json()
        assert body["PropertyId"] == northgate_property_id
        assert body["InspectionId"] == inspection_id
        assert body["InspectionResponseId"] == response_id
        assert first_response["SectionNameSnapshot"] in body["Location"]
        assert first_response["QuestionTextSnapshot"] in body["Location"]
        _delete_issue(db_session, body["MaintenanceIssueId"])
    finally:
        db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection_id).delete()
        db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).delete()
        db_session.commit()


# --- view isolation -----------------------------------------------------------------------

def test_get_issue_belonging_to_another_company_returns_404(
    client: TestClient, db_session: Session, northgate_inspector, bright_spaces_admin, northgate_property_id: int
) -> None:
    create = _create(client, auth_headers(client, northgate_inspector.Email), PropertyId=northgate_property_id)
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        response = client.get(
            f"/api/maintenance-issues/{issue_id}", headers=auth_headers(client, bright_spaces_admin.Email)
        )
        assert response.status_code == 404
    finally:
        _delete_issue(db_session, issue_id)


# --- general edit / assign ----------------------------------------------------------------

def test_update_issue_general_fields_as_admin_succeeds(
    client: TestClient, db_session: Session, northgate_admin, northgate_inspector, northgate_property_id: int
) -> None:
    create = _create(client, auth_headers(client, northgate_inspector.Email), PropertyId=northgate_property_id)
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        response = client.patch(
            f"/api/maintenance-issues/{issue_id}",
            json={"Title": "Leaking tap - kitchen", "Priority": "High"},
            headers=auth_headers(client, northgate_admin.Email),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["Title"] == "Leaking tap - kitchen"
        assert body["Priority"] == "High"
    finally:
        _delete_issue(db_session, issue_id)


def test_update_issue_general_fields_as_assigned_maintenance_user_returns_403(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    northgate_maintenance,
    northgate_inspector,
    northgate_property_id: int,
) -> None:
    create = _create(client, auth_headers(client, northgate_inspector.Email), PropertyId=northgate_property_id)
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        client.patch(
            f"/api/maintenance-issues/{issue_id}/assign",
            json={"AssignedUserId": northgate_maintenance.UserId},
            headers=auth_headers(client, northgate_admin.Email),
        )
        response = client.patch(
            f"/api/maintenance-issues/{issue_id}",
            json={"Title": "Should not be allowed"},
            headers=auth_headers(client, northgate_maintenance.Email),
        )
        assert response.status_code == 403
    finally:
        _delete_issue(db_session, issue_id)


def test_assign_issue_as_admin_moves_open_to_assigned(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    northgate_maintenance,
    northgate_inspector,
    northgate_property_id: int,
) -> None:
    create = _create(client, auth_headers(client, northgate_inspector.Email), PropertyId=northgate_property_id)
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        response = client.patch(
            f"/api/maintenance-issues/{issue_id}/assign",
            json={"AssignedUserId": northgate_maintenance.UserId},
            headers=auth_headers(client, northgate_admin.Email),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["Status"] == "Assigned"
        assert body["AssignedUserId"] == northgate_maintenance.UserId
        assert any(u["UpdateType"] == "StatusChange" and u["NewStatus"] == "Assigned" for u in body["Updates"])
    finally:
        _delete_issue(db_session, issue_id)


# --- status / notes / photos (assigned-or-admin tier) ------------------------------------

def test_status_update_by_assigned_user_succeeds_and_unassigned_user_gets_403(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    northgate_maintenance,
    northgate_maintenance2,
    northgate_inspector,
    northgate_property_id: int,
) -> None:
    create = _create(
        client,
        auth_headers(client, northgate_inspector.Email),
        PropertyId=northgate_property_id,
        AssignedUserId=northgate_maintenance.UserId,
    )
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        forbidden = client.patch(
            f"/api/maintenance-issues/{issue_id}/status",
            json={"NewStatus": "InProgress"},
            headers=auth_headers(client, northgate_maintenance2.Email),
        )
        assert forbidden.status_code == 403

        response = client.patch(
            f"/api/maintenance-issues/{issue_id}/status",
            json={"NewStatus": "InProgress", "Comment": "Started work"},
            headers=auth_headers(client, northgate_maintenance.Email),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["Status"] == "InProgress"
        assert body["Updates"][-1]["Comment"] == "Started work"

        same_status = client.patch(
            f"/api/maintenance-issues/{issue_id}/status",
            json={"NewStatus": "InProgress"},
            headers=auth_headers(client, northgate_maintenance.Email),
        )
        assert same_status.status_code == 422
    finally:
        _delete_issue(db_session, issue_id)


def test_status_update_to_completed_sets_completed_date(
    client: TestClient, db_session: Session, northgate_admin, northgate_inspector, northgate_property_id: int
) -> None:
    create = _create(client, auth_headers(client, northgate_inspector.Email), PropertyId=northgate_property_id)
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        response = client.patch(
            f"/api/maintenance-issues/{issue_id}/status",
            json={"NewStatus": "Completed"},
            headers=auth_headers(client, northgate_admin.Email),
        )
        assert response.status_code == 200
        assert response.json()["CompletedDate"] is not None
    finally:
        _delete_issue(db_session, issue_id)


def test_add_note_by_assigned_user_writes_comment_timeline_entry(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    northgate_maintenance,
    northgate_inspector,
    northgate_property_id: int,
) -> None:
    create = _create(
        client,
        auth_headers(client, northgate_inspector.Email),
        PropertyId=northgate_property_id,
        AssignedUserId=northgate_maintenance.UserId,
    )
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        response = client.post(
            f"/api/maintenance-issues/{issue_id}/notes",
            json={"Comment": "Parts on order"},
            headers=auth_headers(client, northgate_maintenance.Email),
        )
        assert response.status_code == 201
        assert response.json()["UpdateType"] == "Comment"
        assert response.json()["Comment"] == "Parts on order"

        timeline = client.get(
            f"/api/maintenance-issues/{issue_id}/timeline", headers=auth_headers(client, northgate_admin.Email)
        )
        assert timeline.status_code == 200
        assert any(u["Comment"] == "Parts on order" for u in timeline.json())
    finally:
        _delete_issue(db_session, issue_id)


def test_upload_photo_writes_media_and_timeline_entry(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    northgate_maintenance,
    northgate_inspector,
    northgate_property_id: int,
) -> None:
    create = _create(
        client,
        auth_headers(client, northgate_inspector.Email),
        PropertyId=northgate_property_id,
        AssignedUserId=northgate_maintenance.UserId,
    )
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        response = client.post(
            f"/api/maintenance-issues/{issue_id}/photos",
            data={"caption": "Before repair"},
            files={"file": ("before.jpg", b"\xff\xd8\xff\xe0fakejpeg", "image/jpeg")},
            headers=auth_headers(client, northgate_maintenance.Email),
        )
        assert response.status_code == 201
        assert response.json()["EntityType"] == "MaintenanceIssue"
        assert response.json()["EntityId"] == issue_id

        detail = client.get(
            f"/api/maintenance-issues/{issue_id}", headers=auth_headers(client, northgate_admin.Email)
        )
        assert any(u["UpdateType"] == "PhotoUploaded" for u in detail.json()["Updates"])

        media_list = client.get(
            "/api/media",
            params={"entity_type": "MaintenanceIssue", "entity_id": issue_id},
            headers=auth_headers(client, northgate_admin.Email),
        )
        assert media_list.status_code == 200
        assert media_list.json()["total"] == 1
    finally:
        _delete_issue(db_session, issue_id)
