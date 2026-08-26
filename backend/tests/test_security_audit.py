"""
Phase 19 - dedicated cross-company security audit (PROJECT_PLAN.md §11 / §12.1; the doc's own
"scope §20" citation is a pre-existing mislabel - SCOPE.md's real §20 is Pictures/Videos, not
security - not corrected here since fixing doc cross-references wasn't this phase's task).

Every module's own test file already proves cross-company isolation for ITS entity, one at a
time, usually against a throwaway record created just for that test. What no single test file
has done is build ONE full "universe" spanning every entity type this app exposes and check
EVERY read/mutate/create-under-a-foreign-parent path against it in one consolidated pass - the
actual point of a dedicated audit as distinct from N per-module unit tests. Phase 18's IDOR
sweep (test_adversarial.py) proved every detail endpoint 404s for a NONEXISTENT id; this proves
the same for a REAL id genuinely owned by a different real company, which is the guarantee that
actually matters for a multi-tenant system.

Real DB, no mocks, real HTTP via TestClient - same convention as every other test file.
"""
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cleaning_area import CleaningArea
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
from app.models.unit import Unit
from app.models.vacant_unit_inspection import VacantUnitInspection
from tests.conftest import auth_headers, delete_user, make_user

_TINY_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32 + b"\xff\xd9"


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.secaudit.ngadmin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.secaudit.bsadmin.tmp@example.com",
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
def universe(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int, template_id: int
) -> Generator[dict, None, None]:
    """One real record of every entity type this app exposes, all genuinely owned by Northgate.
    Built once via real HTTP calls (not direct DB inserts) so it goes through the exact same
    server-side derivation every real user's request would - the thing being audited."""
    headers = auth_headers(client, northgate_admin.Email)

    unit = client.post(
        f"/api/properties/{northgate_property_id}/units",
        json={"UnitNumber": "Sec-Audit-1"},
        headers=headers,
    ).json()

    area = client.post(
        f"/api/properties/{northgate_property_id}/cleaning-areas",
        json={"AreaName": "Sec Audit Area", "AreaType": "Entrance"},
        headers=headers,
    ).json()

    inspection = client.post(
        "/api/inspections",
        json={"PropertyId": northgate_property_id, "InspectionTemplateId": template_id},
        headers=headers,
    ).json()
    response_id = inspection["Sections"][0]["Responses"][0]["InspectionResponseId"]

    maintenance = client.post(
        "/api/maintenance-issues",
        json={"PropertyId": northgate_property_id, "Title": "Sec audit issue", "Category": "Plumbing"},
        headers=headers,
    ).json()

    risk = client.post(
        "/api/risk-assessments",
        json={
            "PropertyId": northgate_property_id,
            "Hazard": "Sec audit hazard",
            "Likelihood": 2,
            "Severity": 2,
        },
        headers=headers,
    ).json()

    cleaning_inspection = client.post(
        f"/api/inspections/{inspection['InspectionId']}/cleaning",
        json={"CleaningAreaId": area["CleaningAreaId"], "Grade": "A"},
        headers=headers,
    ).json()

    vacant_unit = client.post(
        f"/api/inspections/{inspection['InspectionId']}/vacant-unit-inspections",
        json={"UnitId": unit["UnitId"]},
        headers=headers,
    ).json()

    meter_reading = client.post(
        "/api/meter-readings",
        data={"property_id": northgate_property_id, "meter_type": "Electricity"},
        files={"file": ("meter.jpg", _TINY_JPEG, "image/jpeg")},
        headers=headers,
    ).json()

    media = client.post(
        "/api/media",
        data={"entity_type": "Property", "entity_id": northgate_property_id},
        files={"file": ("evidence.jpg", _TINY_JPEG, "image/jpeg")},
        headers=headers,
    ).json()

    ids = {
        "property_id": northgate_property_id,
        "unit_id": unit["UnitId"],
        "cleaning_area_id": area["CleaningAreaId"],
        "inspection_id": inspection["InspectionId"],
        "response_id": response_id,
        "maintenance_issue_id": maintenance["MaintenanceIssueId"],
        "risk_assessment_id": risk["RiskAssessmentId"],
        "cleaning_inspection_id": cleaning_inspection["CleaningInspectionId"],
        "vacant_unit_inspection_id": vacant_unit["VacantUnitInspectionId"],
        "meter_reading_id": meter_reading["MeterReadingId"],
        "media_file_id": media["MediaFileId"],
    }

    try:
        yield ids
    finally:
        for m in db_session.execute(
            select(MediaFile).where(MediaFile.EntityType == "MaintenanceIssue", MediaFile.EntityId == maintenance["MaintenanceIssueId"])
        ).scalars().all():
            (Path(settings.MEDIA_UPLOAD_DIR) / m.StorageKey).unlink(missing_ok=True)
            db_session.delete(m)
        db_session.commit()

        media_row = db_session.get(MediaFile, media["MediaFileId"])
        if media_row is not None:
            (Path(settings.MEDIA_UPLOAD_DIR) / media_row.StorageKey).unlink(missing_ok=True)
            db_session.delete(media_row)
        db_session.commit()

        # MeterReading.PhotoMediaFileId FKs to MediaFiles with no ORM relationship() to let
        # SQLAlchemy infer delete order automatically - the MeterReading row itself must be
        # deleted BEFORE its photo, not the other way round (hit this for real: deleting the
        # photo first threw FK_MeterReadings_MediaFiles).
        meter_row = db_session.get(MeterReading, meter_reading["MeterReadingId"])
        if meter_row is not None:
            photo_id = meter_row.PhotoMediaFileId
            db_session.delete(meter_row)
            db_session.commit()
            if photo_id is not None:
                photo = db_session.get(MediaFile, photo_id)
                if photo is not None:
                    (Path(settings.MEDIA_UPLOAD_DIR) / photo.StorageKey).unlink(missing_ok=True)
                    db_session.delete(photo)
                    db_session.commit()

        db_session.query(VacantUnitInspection).filter(
            VacantUnitInspection.VacantUnitInspectionId == vacant_unit["VacantUnitInspectionId"]
        ).delete()
        db_session.query(CleaningInspection).filter(
            CleaningInspection.CleaningInspectionId == cleaning_inspection["CleaningInspectionId"]
        ).delete()
        db_session.query(RiskAssessment).filter(RiskAssessment.RiskAssessmentId == risk["RiskAssessmentId"]).delete()
        db_session.query(MaintenanceUpdate).filter(
            MaintenanceUpdate.MaintenanceIssueId == maintenance["MaintenanceIssueId"]
        ).delete()
        db_session.query(MaintenanceIssue).filter(
            MaintenanceIssue.MaintenanceIssueId == maintenance["MaintenanceIssueId"]
        ).delete()
        db_session.commit()

        db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection["InspectionId"]).delete()
        db_session.query(Inspection).filter(Inspection.InspectionId == inspection["InspectionId"]).delete()
        db_session.query(CleaningArea).filter(CleaningArea.CleaningAreaId == area["CleaningAreaId"]).delete()
        db_session.query(Unit).filter(Unit.UnitId == unit["UnitId"]).delete()
        db_session.commit()


# --- read/mutate an EXISTING record genuinely owned by another company ----------------------
# Every one of these must 404 (never 403 - a foreign-owned record must be indistinguishable
# from one that doesn't exist, the isolation rule this whole project has followed since Phase 6).


def _foreign_get_and_mutate_cases(ids: dict) -> list[tuple[str, str, dict | None]]:
    return [
        ("GET", f"/api/properties/{ids['property_id']}/units", None),
        ("GET", f"/api/units/{ids['unit_id']}", None),
        ("PATCH", f"/api/units/{ids['unit_id']}", {"Notes": "hijacked"}),
        ("PATCH", f"/api/units/{ids['unit_id']}/occupancy", {"OccupancyStatus": "Vacant"}),
        ("GET", f"/api/properties/{ids['property_id']}/cleaning-areas", None),
        ("PATCH", f"/api/cleaning-areas/{ids['cleaning_area_id']}", {"AreaName": "hijacked"}),
        ("GET", f"/api/inspections/{ids['inspection_id']}", None),
        ("PATCH", f"/api/inspections/{ids['inspection_id']}", {"GeneralNotes": "hijacked"}),
        ("GET", f"/api/inspections/{ids['inspection_id']}/report", None),
        ("POST", f"/api/inspections/{ids['inspection_id']}/submit", None),
        (
            "PATCH",
            f"/api/inspections/{ids['inspection_id']}/responses/{ids['response_id']}",
            {"AnswerText": "Yes"},
        ),
        ("GET", f"/api/inspections/{ids['inspection_id']}/cleaning", None),
        ("GET", f"/api/inspections/{ids['inspection_id']}/vacant-unit-inspections", None),
        ("GET", f"/api/maintenance-issues/{ids['maintenance_issue_id']}", None),
        ("GET", f"/api/maintenance-issues/{ids['maintenance_issue_id']}/timeline", None),
        ("PATCH", f"/api/maintenance-issues/{ids['maintenance_issue_id']}", {"Title": "hijacked"}),
        (
            "PATCH",
            f"/api/maintenance-issues/{ids['maintenance_issue_id']}/assign",
            {"AssignedUserId": 1},
        ),
        (
            "PATCH",
            f"/api/maintenance-issues/{ids['maintenance_issue_id']}/status",
            {"NewStatus": "InProgress"},
        ),
        ("POST", f"/api/maintenance-issues/{ids['maintenance_issue_id']}/notes", {"Comment": "hijacked"}),
        ("GET", f"/api/risk-assessments/{ids['risk_assessment_id']}", None),
        ("PATCH", f"/api/risk-assessments/{ids['risk_assessment_id']}", {"Notes": "hijacked"}),
        ("PATCH", f"/api/cleaning-inspections/{ids['cleaning_inspection_id']}", {"Grade": "E"}),
        ("GET", f"/api/cleaning-inspections/{ids['cleaning_inspection_id']}", None),
        (
            "PATCH",
            f"/api/vacant-unit-inspections/{ids['vacant_unit_inspection_id']}",
            {"Notes": "hijacked"},
        ),
        ("GET", f"/api/vacant-unit-inspections/{ids['vacant_unit_inspection_id']}", None),
        ("GET", f"/api/meter-readings/{ids['meter_reading_id']}", None),
        ("PATCH", f"/api/meter-readings/{ids['meter_reading_id']}", {"ConfirmedReading": "999"}),
        ("GET", f"/api/media/{ids['media_file_id']}", None),
        ("GET", f"/api/media/{ids['media_file_id']}/download", None),
        ("PATCH", f"/api/media/{ids['media_file_id']}", {"Caption": "hijacked"}),
        ("DELETE", f"/api/media/{ids['media_file_id']}", None),
    ]


def test_foreign_company_cannot_read_or_mutate_any_real_record(
    client: TestClient, bright_spaces_admin, universe: dict
) -> None:
    headers = auth_headers(client, bright_spaces_admin.Email)
    failures = []
    for method, path, body in _foreign_get_and_mutate_cases(universe):
        response = client.request(method, path, json=body, headers=headers)
        if response.status_code != 404:
            failures.append(f"{method} {path} -> {response.status_code} (expected 404)")
    assert not failures, "Cross-company isolation violations:\n" + "\n".join(failures)


# --- create a CHILD record under a parent genuinely owned by another company -----------------
# The other half of the guarantee: not just "can't touch their existing records" but "can't
# plant new data inside their tenant either."


def _foreign_create_cases(ids: dict) -> list[tuple[str, str, dict]]:
    return [
        ("POST", f"/api/properties/{ids['property_id']}/units", {"UnitNumber": "Planted"}),
        (
            "POST",
            f"/api/properties/{ids['property_id']}/cleaning-areas",
            {"AreaName": "Planted", "AreaType": "Entrance"},
        ),
        (
            "POST",
            f"/api/inspections/{ids['inspection_id']}/cleaning",
            {"CleaningAreaId": ids["cleaning_area_id"], "Grade": "A"},
        ),
        (
            "POST",
            f"/api/inspections/{ids['inspection_id']}/vacant-unit-inspections",
            {"UnitId": ids["unit_id"]},
        ),
        ("POST", "/api/maintenance-issues", {"PropertyId": ids["property_id"], "Title": "Planted", "Category": "Plumbing"}),
        (
            "POST",
            "/api/risk-assessments",
            {"PropertyId": ids["property_id"], "Hazard": "Planted", "Likelihood": 1, "Severity": 1},
        ),
    ]


def test_foreign_company_cannot_create_child_records_under_another_companys_parent(
    client: TestClient, bright_spaces_admin, universe: dict
) -> None:
    headers = auth_headers(client, bright_spaces_admin.Email)
    failures = []
    for method, path, body in _foreign_create_cases(universe):
        response = client.request(method, path, json=body, headers=headers)
        if response.status_code != 404:
            failures.append(f"{method} {path} -> {response.status_code} (expected 404)")
    assert not failures, "Cross-tenant planting violations:\n" + "\n".join(failures)


def test_foreign_company_start_inspection_on_property_returns_404(
    client: TestClient, bright_spaces_admin, northgate_property_id: int, db_session: Session, template_id: int
) -> None:
    """Separate from the universe fixture since a successful (bug) start would create its own
    Inspection that needs its own cleanup."""
    headers = auth_headers(client, bright_spaces_admin.Email)
    response = client.post(
        "/api/inspections",
        json={"PropertyId": northgate_property_id, "InspectionTemplateId": template_id},
        headers=headers,
    )
    assert response.status_code == 404


def test_foreign_company_meter_reading_create_on_property_returns_404(
    client: TestClient, bright_spaces_admin, northgate_property_id: int, db_session: Session
) -> None:
    headers = auth_headers(client, bright_spaces_admin.Email)
    response = client.post(
        "/api/meter-readings",
        data={"property_id": northgate_property_id, "meter_type": "Electricity"},
        files={"file": ("meter.jpg", _TINY_JPEG, "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 404
    # Guard against a bug creating a real row despite the 404 - fail loudly rather than leave
    # orphaned test data if this ever regresses.
    if response.status_code == 201:
        reading_id = response.json()["MeterReadingId"]
        db_session.query(MeterReading).filter(MeterReading.MeterReadingId == reading_id).delete()
        db_session.commit()


def test_foreign_company_media_upload_on_property_returns_404(
    client: TestClient, bright_spaces_admin, northgate_property_id: int, db_session: Session
) -> None:
    headers = auth_headers(client, bright_spaces_admin.Email)
    response = client.post(
        "/api/media",
        data={"entity_type": "Property", "entity_id": northgate_property_id},
        files={"file": ("evidence.jpg", _TINY_JPEG, "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 404
    if response.status_code == 201:
        media_id = response.json()["MediaFileId"]
        media_row = db_session.get(MediaFile, media_id)
        if media_row is not None:
            (Path(settings.MEDIA_UPLOAD_DIR) / media_row.StorageKey).unlink(missing_ok=True)
            db_session.delete(media_row)
            db_session.commit()


# --- denormalized CompanyId never drifts from its parent -------------------------------------
# docs/DATABASE.md §10.1's own flagged risk: MaintenanceIssues/RiskAssessments/MediaFiles carry
# their own CompanyId column instead of always deriving it via a join. Confirms it's never
# actually left to drift - every record created through the real API has a CompanyId that
# matches its parent Property/Company exactly, not just "close enough."


def test_denormalized_company_id_matches_parent_on_every_created_record(
    db_session: Session, universe: dict, northgate_admin
) -> None:
    company_id = northgate_admin.CompanyId

    maintenance = db_session.get(MaintenanceIssue, universe["maintenance_issue_id"])
    assert maintenance.CompanyId == company_id

    risk = db_session.get(RiskAssessment, universe["risk_assessment_id"])
    assert risk.CompanyId == company_id

    media = db_session.get(MediaFile, universe["media_file_id"])
    assert media.CompanyId == company_id
