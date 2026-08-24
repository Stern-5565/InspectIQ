"""Risk Assessment API tests - same conventions as test_maintenance.py (real DB, no mocks,
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
from app.models.property import Property
from app.models.risk_assessment import RiskAssessment
from app.models.risk_matrix_level import RiskMatrixLevel
from tests.conftest import auth_headers, delete_user, make_user


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.risk.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.risk.inspector.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_maintenance(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.risk.maintenance.tmp@example.com",
        role_name="Maintenance",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.risk.bsadmin.tmp@example.com",
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


def _delete_risk_assessment(db_session: Session, risk_assessment_id: int) -> None:
    media = db_session.execute(
        select(MediaFile).where(
            MediaFile.EntityType == "RiskAssessment", MediaFile.EntityId == risk_assessment_id
        )
    ).scalars().all()
    for m in media:
        (Path(settings.MEDIA_UPLOAD_DIR) / m.StorageKey).unlink(missing_ok=True)
        db_session.delete(m)
    db_session.query(RiskAssessment).filter(RiskAssessment.RiskAssessmentId == risk_assessment_id).delete()
    db_session.commit()


def _create(client: TestClient, headers: dict, **overrides) -> "TestClient":
    payload = {"Hazard": "Loose handrail", "Likelihood": 3, "Severity": 3, **overrides}
    return client.post("/api/risk-assessments", json=payload, headers=headers)


# --- create ------------------------------------------------------------------------------------


def test_create_standalone_as_admin_computes_score_and_level(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    response = _create(client, headers, PropertyId=northgate_property_id, Likelihood=4, Severity=5)

    try:
        assert response.status_code == 201
        body = response.json()
        assert body["PropertyId"] == northgate_property_id
        assert body["RiskScore"] == 20
        assert body["RiskLevel"] == "Critical"
        assert body["Status"] == "Open"
    finally:
        _delete_risk_assessment(db_session, response.json()["RiskAssessmentId"])


def test_risk_level_matches_global_matrix_band(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    response = _create(client, headers, PropertyId=northgate_property_id, Likelihood=2, Severity=3)

    try:
        assert response.status_code == 201
        assert response.json()["RiskScore"] == 6
        assert response.json()["RiskLevel"] == "Medium"
    finally:
        _delete_risk_assessment(db_session, response.json()["RiskAssessmentId"])


def test_create_as_inspector_succeeds(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int
) -> None:
    response = _create(
        client, auth_headers(client, northgate_inspector.Email), PropertyId=northgate_property_id
    )
    try:
        assert response.status_code == 201
    finally:
        _delete_risk_assessment(db_session, response.json()["RiskAssessmentId"])


def test_create_as_maintenance_role_returns_403(
    client: TestClient, northgate_maintenance, northgate_property_id: int
) -> None:
    response = _create(
        client, auth_headers(client, northgate_maintenance.Email), PropertyId=northgate_property_id
    )
    assert response.status_code == 403


def test_create_without_property_or_inspection_returns_422(
    client: TestClient, northgate_admin
) -> None:
    response = _create(client, auth_headers(client, northgate_admin.Email))
    assert response.status_code == 422


def test_create_for_property_in_another_company_returns_404(
    client: TestClient, bright_spaces_admin, northgate_property_id: int
) -> None:
    response = _create(
        client, auth_headers(client, bright_spaces_admin.Email), PropertyId=northgate_property_id
    )
    assert response.status_code == 404


def test_create_from_inspection_response_derives_property_and_inspection(
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
        response = _create(client, headers, InspectionResponseId=response_id)
        assert response.status_code == 201
        body = response.json()
        assert body["PropertyId"] == northgate_property_id
        assert body["InspectionId"] == inspection_id
        assert body["InspectionResponseId"] == response_id
        _delete_risk_assessment(db_session, body["RiskAssessmentId"])
    finally:
        db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection_id).delete()
        db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).delete()
        db_session.commit()


# --- view / update -------------------------------------------------------------------------

def test_get_risk_assessment_in_another_company_returns_404(
    client: TestClient, db_session: Session, northgate_admin, bright_spaces_admin, northgate_property_id: int
) -> None:
    create = _create(client, auth_headers(client, northgate_admin.Email), PropertyId=northgate_property_id)
    risk_assessment_id = create.json()["RiskAssessmentId"]

    try:
        response = client.get(
            f"/api/risk-assessments/{risk_assessment_id}", headers=auth_headers(client, bright_spaces_admin.Email)
        )
        assert response.status_code == 404
    finally:
        _delete_risk_assessment(db_session, risk_assessment_id)


def test_update_as_admin_recomputes_risk_level(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    create = _create(
        client, auth_headers(client, northgate_admin.Email), PropertyId=northgate_property_id, Likelihood=1, Severity=1
    )
    risk_assessment_id = create.json()["RiskAssessmentId"]
    assert create.json()["RiskLevel"] == "Low"

    try:
        response = client.patch(
            f"/api/risk-assessments/{risk_assessment_id}",
            json={"Severity": 5, "Status": "ActionPlanned", "Notes": "Escalated"},
            headers=auth_headers(client, northgate_admin.Email),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["RiskScore"] == 5
        assert body["RiskLevel"] == "Medium"
        assert body["Status"] == "ActionPlanned"
        assert body["Notes"] == "Escalated"
        assert body["Hazard"] == "Loose handrail"  # untouched
    finally:
        _delete_risk_assessment(db_session, risk_assessment_id)


def test_update_as_inspector_returns_403_even_for_creator(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    create = _create(client, headers, PropertyId=northgate_property_id)
    risk_assessment_id = create.json()["RiskAssessmentId"]

    try:
        response = client.patch(
            f"/api/risk-assessments/{risk_assessment_id}", json={"Notes": "Should not be allowed"}, headers=headers
        )
        assert response.status_code == 403
    finally:
        _delete_risk_assessment(db_session, risk_assessment_id)


# --- risk matrix ---------------------------------------------------------------------------

def test_get_risk_matrix_returns_global_default(client: TestClient, northgate_admin) -> None:
    response = client.get("/api/risk-matrix-levels", headers=auth_headers(client, northgate_admin.Email))
    assert response.status_code == 200
    levels = response.json()
    assert {lvl["LevelName"] for lvl in levels} == {"Low", "Medium", "High", "Critical"}
    assert all(lvl["CompanyId"] is None for lvl in levels)


def test_company_override_matrix_fully_replaces_global_default(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    admin_headers = auth_headers(client, northgate_admin.Email)
    create_level = client.post(
        "/api/risk-matrix-levels",
        json={"MinScore": 1, "MaxScore": 25, "LevelName": "Custom", "ColorHint": "#000000"},
        headers=admin_headers,
    )
    level_id = create_level.json()["RiskMatrixLevelId"]

    try:
        assert create_level.status_code == 201

        matrix = client.get("/api/risk-matrix-levels", headers=admin_headers)
        assert matrix.status_code == 200
        assert len(matrix.json()) == 1
        assert matrix.json()[0]["LevelName"] == "Custom"

        # A new assessment for this company now resolves against the override, not the global
        # default - any score 1-25 lands in the one custom band.
        ra = _create(client, admin_headers, PropertyId=northgate_property_id, Likelihood=1, Severity=1)
        try:
            assert ra.status_code == 201
            assert ra.json()["RiskLevel"] == "Custom"
        finally:
            _delete_risk_assessment(db_session, ra.json()["RiskAssessmentId"])

        # Bright Spaces (a different company) is unaffected - still sees the global default.
    finally:
        db_session.query(RiskMatrixLevel).filter(RiskMatrixLevel.RiskMatrixLevelId == level_id).delete()
        db_session.commit()


def test_other_company_unaffected_by_this_companys_override(
    client: TestClient, db_session: Session, northgate_admin, bright_spaces_admin
) -> None:
    create_level = client.post(
        "/api/risk-matrix-levels",
        json={"MinScore": 1, "MaxScore": 25, "LevelName": "Custom", "ColorHint": "#000000"},
        headers=auth_headers(client, northgate_admin.Email),
    )
    level_id = create_level.json()["RiskMatrixLevelId"]

    try:
        bs_matrix = client.get(
            "/api/risk-matrix-levels", headers=auth_headers(client, bright_spaces_admin.Email)
        )
        assert {lvl["LevelName"] for lvl in bs_matrix.json()} == {"Low", "Medium", "High", "Critical"}
    finally:
        db_session.query(RiskMatrixLevel).filter(RiskMatrixLevel.RiskMatrixLevelId == level_id).delete()
        db_session.commit()


def test_create_risk_matrix_level_as_inspector_returns_403(client: TestClient, northgate_inspector) -> None:
    response = client.post(
        "/api/risk-matrix-levels",
        json={"MinScore": 1, "MaxScore": 25, "LevelName": "Custom"},
        headers=auth_headers(client, northgate_inspector.Email),
    )
    assert response.status_code == 403


def test_create_risk_matrix_level_with_min_greater_than_max_returns_422(
    client: TestClient, db_session: Session, northgate_admin
) -> None:
    response = client.post(
        "/api/risk-matrix-levels",
        json={"MinScore": 10, "MaxScore": 5, "LevelName": "Backwards"},
        headers=auth_headers(client, northgate_admin.Email),
    )
    assert response.status_code == 422
    # Nothing should have been created, but defensively clean up if the validation somehow let
    # a row through - keeps this test from ever poisoning the company's matrix.
    db_session.query(RiskMatrixLevel).filter(RiskMatrixLevel.LevelName == "Backwards").delete()
    db_session.commit()


# --- media integration -----------------------------------------------------------------------


def test_upload_photo_by_inspector_who_cannot_edit_the_record(
    client: TestClient, db_session: Session, northgate_admin, northgate_inspector, northgate_property_id: int
) -> None:
    create = _create(client, auth_headers(client, northgate_admin.Email), PropertyId=northgate_property_id)
    risk_assessment_id = create.json()["RiskAssessmentId"]

    try:
        # The Inspector can't PATCH this record (Admin/Manager-only, tested above) but scope
        # gives "upload evidence" as its own broader capability - same as Property/Unit.
        upload = client.post(
            "/api/media",
            data={"entity_type": "RiskAssessment", "entity_id": risk_assessment_id},
            files={"file": ("hazard.jpg", b"\xff\xd8\xff\xe0fake", "image/jpeg")},
            headers=auth_headers(client, northgate_inspector.Email),
        )
        assert upload.status_code == 201

        listing = client.get(
            "/api/media",
            params={"entity_type": "RiskAssessment", "entity_id": risk_assessment_id},
            headers=auth_headers(client, northgate_admin.Email),
        )
        assert listing.status_code == 200
        assert listing.json()["total"] == 1
    finally:
        _delete_risk_assessment(db_session, risk_assessment_id)
