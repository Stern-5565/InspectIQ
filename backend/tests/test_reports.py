"""PDF Inspection Report tests (Phase 17) - same conventions as every other test file (real DB,
no mocks, explicit cleanup). Builds one genuinely rich submitted inspection (a Fail answer, a
real embedded photo, a maintenance issue, a risk assessment, a meter reading) so the 200 case
exercises every section report_service.py builds, not just an empty shell."""
from collections.abc import Generator
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image as PILImage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cleaning_inspection import CleaningInspection
from app.models.inspection import Inspection
from app.models.inspection_response import InspectionResponse
from app.models.inspection_template import InspectionTemplate
from app.models.maintenance_issue import MaintenanceIssue
from app.models.maintenance_update import MaintenanceUpdate
from app.models.media_file import MediaFile
from app.models.meter_reading import MeterReading
from app.models.property import Property
from app.models.risk_assessment import RiskAssessment
from app.models.vacant_unit_inspection import VacantUnitInspection
from tests.conftest import auth_headers, delete_user, make_user


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.reports.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.reports.inspector.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.reports.bsadmin.tmp@example.com",
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


def _real_jpeg_bytes() -> bytes:
    """A genuine, tiny, PIL-decodable JPEG - unlike every other test file's `b"\\xff\\xd8...
    fake"` placeholder, this one needs to actually survive report_service.py's real PIL-based
    scaling step, not just satisfy a ContentType check."""
    buf = BytesIO()
    PILImage.new("RGB", (40, 30), color="red").save(buf, format="JPEG")
    return buf.getvalue()


def _start_inspection(client: TestClient, headers: dict, property_id: int, template_id: int) -> dict:
    response = client.post(
        "/api/inspections",
        json={"PropertyId": property_id, "InspectionTemplateId": template_id},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _delete_inspection_and_children(db_session: Session, inspection_id: int) -> None:
    """Cleans up every module a report might touch - not just Inspection/InspectionResponse.
    Order matters: MeterReadings.PhotoMediaFileId is a real FK to MediaFiles (same gotcha
    test_meter_readings.py's own _delete_reading works around), so MeterReading/MaintenanceIssue
    rows are deleted BEFORE the MediaFiles they may reference, which are deleted BEFORE the
    InspectionResponses/Inspection those media rows point back to via EntityId."""
    response_ids = [
        r.InspectionResponseId
        for r in db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection_id)
    ]
    meter_readings = (
        list(db_session.query(MeterReading).filter(MeterReading.InspectionResponseId.in_(response_ids)))
        if response_ids
        else []
    )
    maintenance_issues = list(
        db_session.query(MaintenanceIssue).filter(MaintenanceIssue.InspectionId == inspection_id)
    )

    media_entity_pairs = [("InspectionResponse", rid) for rid in response_ids]
    media_entity_pairs += [("MeterReading", r.MeterReadingId) for r in meter_readings]
    media_entity_pairs += [("MaintenanceIssue", m.MaintenanceIssueId) for m in maintenance_issues]

    media_files = []
    for entity_type, entity_id in media_entity_pairs:
        media_files += list(
            db_session.execute(
                select(MediaFile).where(MediaFile.EntityType == entity_type, MediaFile.EntityId == entity_id)
            ).scalars()
        )

    if response_ids:
        db_session.query(MeterReading).filter(MeterReading.InspectionResponseId.in_(response_ids)).delete(
            synchronize_session=False
        )
    db_session.query(MaintenanceUpdate).filter(
        MaintenanceUpdate.MaintenanceIssueId.in_([m.MaintenanceIssueId for m in maintenance_issues])
    ).delete(synchronize_session=False)
    db_session.query(MaintenanceIssue).filter(MaintenanceIssue.InspectionId == inspection_id).delete()
    db_session.query(RiskAssessment).filter(RiskAssessment.InspectionId == inspection_id).delete()
    db_session.query(CleaningInspection).filter(CleaningInspection.InspectionId == inspection_id).delete()
    db_session.query(VacantUnitInspection).filter(VacantUnitInspection.InspectionId == inspection_id).delete()
    db_session.commit()

    for media in media_files:
        (Path(settings.MEDIA_UPLOAD_DIR) / media.StorageKey).unlink(missing_ok=True)
        db_session.delete(media)
    db_session.commit()

    db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection_id).delete()
    db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).delete()
    db_session.commit()


# --- the rich, real, end-to-end case ------------------------------------------------------------


def test_report_for_submitted_inspection_returns_real_pdf_with_every_section(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    northgate_property_id: int,
    template_id: int,
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)
    inspection_id = body["InspectionId"]
    all_responses = [r for section in body["Sections"] for r in section["Responses"]]

    try:
        fail_response = next(r for r in all_responses if r["AnswerTypeSnapshot"] == "PassFail")
        client.patch(
            f"/api/inspections/{inspection_id}/responses/{fail_response['InspectionResponseId']}",
            json={"AnswerText": "Fail"},
            headers=headers,
        )
        upload = client.post(
            "/api/media",
            data={"entity_type": "InspectionResponse", "entity_id": fail_response["InspectionResponseId"]},
            files={"file": ("fail_evidence.jpg", _real_jpeg_bytes(), "image/jpeg")},
            headers=headers,
        )
        assert upload.status_code == 201

        for r in all_responses:
            if r["InspectionResponseId"] != fail_response["InspectionResponseId"]:
                client.patch(
                    f"/api/inspections/{inspection_id}/responses/{r['InspectionResponseId']}",
                    json={"IsNotApplicable": True},
                    headers=headers,
                )

        maintenance = client.post(
            "/api/maintenance-issues",
            json={
                "InspectionResponseId": fail_response["InspectionResponseId"],
                "Title": "Broken fire door",
                "Category": "FireSafety",
                "Priority": "High",
            },
            headers=headers,
        )
        assert maintenance.status_code == 201

        risk = client.post(
            "/api/risk-assessments",
            json={
                "InspectionResponseId": fail_response["InspectionResponseId"],
                "Hazard": "Fire door does not self-close",
                "Likelihood": 4,
                "Severity": 4,
            },
            headers=headers,
        )
        assert risk.status_code == 201

        meter = client.post(
            "/api/meter-readings",
            data={
                "property_id": northgate_property_id,
                "meter_type": "Electricity",
                "inspection_response_id": fail_response["InspectionResponseId"],
            },
            files={"file": ("meter.jpg", _real_jpeg_bytes(), "image/jpeg")},
            headers=headers,
        )
        assert meter.status_code == 201

        submit = client.post(f"/api/inspections/{inspection_id}/submit", headers=headers)
        assert submit.status_code == 200

        report = client.get(f"/api/inspections/{inspection_id}/report", headers=headers)
        assert report.status_code == 200
        assert report.headers["content-type"] == "application/pdf"
        assert f"Inspection-{inspection_id}-Report.pdf" in report.headers["content-disposition"]
        assert report.content.startswith(b"%PDF")
        assert len(report.content) > 2000  # a real, multi-section document, not an empty shell
    finally:
        _delete_inspection_and_children(db_session, inspection_id)


# --- edge cases ------------------------------------------------------------------------------


def test_report_for_in_progress_inspection_returns_409(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)

    try:
        response = client.get(f"/api/inspections/{body['InspectionId']}/report", headers=headers)
        assert response.status_code == 409
    finally:
        _delete_inspection_and_children(db_session, body["InspectionId"])


def test_report_for_inspection_in_another_company_returns_404(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    bright_spaces_admin,
    northgate_property_id: int,
    template_id: int,
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)

    try:
        response = client.get(
            f"/api/inspections/{body['InspectionId']}/report",
            headers=auth_headers(client, bright_spaces_admin.Email),
        )
        assert response.status_code == 404
    finally:
        _delete_inspection_and_children(db_session, body["InspectionId"])
