"""
Phase 18 - adversarial testing pass (scope's "Prompt 19" testing phase, PROJECT_PLAN.md §11).

Deliberately does NOT re-test what every module's own test file already covers per-endpoint
(role gating, basic cross-company 404s, CRUD happy paths - 155 tests already do that). This file
targets attack surface that only shows up when you go looking for it on purpose: token forgery,
mass-assignment attempts, IDOR via ID-guessing, injection-style payloads, upload abuse, and a
genuine concurrent (not just sequential) double-submit race.

Real DB, no mocks - same convention as every other test file in this project.
"""
import threading
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.inspection import Inspection
from app.models.inspection_response import InspectionResponse
from app.models.inspection_template import InspectionTemplate
from app.models.cleaning_area import CleaningArea
from app.models.maintenance_issue import MaintenanceIssue
from app.models.maintenance_update import MaintenanceUpdate
from app.models.media_file import MediaFile
from app.models.property import Property
from app.models.risk_assessment import RiskAssessment
from app.security.jwt import ACCESS_TOKEN_TYPE
from tests.conftest import auth_headers, delete_user, make_user

_NONEXISTENT_ID = 999_999_999


def _delete_maintenance_issue(db_session: Session, issue_id: int) -> None:
    """MaintenanceIssues has an FK'd MaintenanceUpdates timeline (every status/edit action can
    write one) - same cleanup order test_maintenance.py's own _delete_issue already established."""
    db_session.query(MaintenanceUpdate).filter(MaintenanceUpdate.MaintenanceIssueId == issue_id).delete()
    db_session.query(MaintenanceIssue).filter(MaintenanceIssue.MaintenanceIssueId == issue_id).delete()
    db_session.commit()


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.adversarial.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.adversarial.inspector.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.adversarial.bsadmin.tmp@example.com",
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


# --- token forgery -------------------------------------------------------------------------
# test_me_rejects_garbage_token (test_auth.py) already covers a structurally-invalid string.
# These target a well-FORMED JWT that's forged, expired, or downgrades its own algorithm -
# a materially different attack than "garbage" and not covered anywhere else.


def test_tampered_signature_token_rejected(client: TestClient, northgate_admin) -> None:
    """A token re-signed with the wrong key (e.g. an attacker who guessed the payload shape
    but not the real secret) must be rejected, not just a token with corrupted structure."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(northgate_admin.UserId),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    forged = pyjwt.encode(payload, "totally-wrong-secret-key-that-is-long-enough", algorithm=settings.JWT_ALGORITHM)

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_expired_access_token_rejected(client: TestClient, northgate_admin) -> None:
    """Crafted directly with an already-past exp, rather than waiting out the real 30-minute
    expiry - proves expiry is actually enforced, not just assumed from the library default."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(northgate_admin.UserId),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now - timedelta(hours=1),
        "exp": now - timedelta(minutes=1),
    }
    expired = pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_alg_none_token_rejected(client: TestClient, northgate_admin) -> None:
    """The classic JWT 'alg: none' downgrade attack - a token with no signature at all, relying
    on a permissive verifier accepting unsigned tokens. decode_token pins `algorithms=
    [settings.JWT_ALGORITHM]` (app/security/jwt.py), which should make this structurally
    impossible, not just unlikely."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(northgate_admin.UserId),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    unsigned = pyjwt.encode(payload, key=None, algorithm="none")

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {unsigned}"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "header_value",
    ["", "Bearer", "Bearer ", "NotBearer sometoken", "Basic dXNlcjpwYXNz"],
)
def test_malformed_authorization_header_variants_rejected(client: TestClient, header_value: str) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": header_value})
    assert response.status_code == 401


def test_refresh_token_type_confusion_on_wrong_endpoint_direction(client: TestClient, northgate_admin) -> None:
    """The inverse of test_auth.py's existing 'refresh token used as access token' check: an
    ACCESS token replayed at the /refresh endpoint must also be rejected by the same type check,
    not just one direction of it."""
    login = client.post(
        "/api/auth/login", json={"email": northgate_admin.Email, "password": "Test-Password-123!"}
    )
    access_token = login.json()["access_token"]

    response = client.post("/api/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


# --- mass assignment -------------------------------------------------------------------------
# None of these fields exist on their respective Create/Update schemas (verified by reading the
# schema files), so pydantic silently drops them - these tests prove that holds at the live HTTP
# boundary too, not just by reading the code.


def test_property_create_ignores_client_supplied_company_id(
    client: TestClient, db_session: Session, northgate_admin, bright_spaces_admin
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    bright_spaces_company_id = bright_spaces_admin.CompanyId

    response = client.post(
        "/api/properties",
        json={
            "PropertyName": "Adversarial Mass-Assignment Test Property",
            "AddressLine1": "1 Test Street",
            "Postcode": "AB1 2CD",
            "PropertyType": "ResidentialHouse",
            "InspectionFrequency": "Monthly",
            "CompanyId": bright_spaces_company_id,  # attacker-controlled, must be ignored
        },
        headers=headers,
    )
    assert response.status_code == 201
    created = response.json()
    property_id = created["PropertyId"]

    try:
        # Confirm it landed under the ACTING user's company, not the injected one, by checking
        # a Bright Spaces admin still gets 404 on it.
        bs_response = client.get(
            f"/api/properties/{property_id}", headers=auth_headers(client, bright_spaces_admin.Email)
        )
        assert bs_response.status_code == 404
        ng_response = client.get(f"/api/properties/{property_id}", headers=headers)
        assert ng_response.status_code == 200
    finally:
        # Every real property auto-seeds 3 CleaningAreas (Phase 11) - same cleanup order
        # test_properties.py's own _delete_property already established.
        db_session.query(CleaningArea).filter(CleaningArea.PropertyId == property_id).delete()
        db_session.query(Property).filter(Property.PropertyId == property_id).delete()
        db_session.commit()


def test_maintenance_update_ignores_client_supplied_status_and_ids(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    create = client.post(
        "/api/maintenance-issues",
        json={
            "PropertyId": northgate_property_id,
            "Title": "Adversarial mass-assignment test issue",
            "Category": "Plumbing",
        },
        headers=headers,
    )
    assert create.status_code == 201
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        patch = client.patch(
            f"/api/maintenance-issues/{issue_id}",
            json={
                "Title": "Updated title",
                "Status": "Completed",  # not on MaintenanceIssueUpdate - must be silently dropped
                "CompanyId": _NONEXISTENT_ID,
                "AssignedUserId": _NONEXISTENT_ID,  # also has its own dedicated endpoint
            },
            headers=headers,
        )
        assert patch.status_code == 200
        body = patch.json()
        assert body["Title"] == "Updated title"
        assert body["Status"] == "Open"  # unchanged - general PATCH cannot move workflow state
        assert body["AssignedUserId"] is None
    finally:
        _delete_maintenance_issue(db_session, issue_id)


def test_risk_assessment_create_ignores_client_supplied_risk_score(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    response = client.post(
        "/api/risk-assessments",
        json={
            "PropertyId": northgate_property_id,
            "Hazard": "Adversarial mass-assignment test hazard",
            "Likelihood": 1,
            "Severity": 1,
            "RiskScore": 999,  # not on RiskAssessmentCreate - a real PERSISTED computed column
            "RiskLevel": "Critical",
            "Status": "Closed",
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    risk_id = body["RiskAssessmentId"]

    try:
        assert body["RiskScore"] == 1  # genuinely computed as Likelihood(1) * Severity(1)
        assert body["Status"] == "Open"  # every new assessment starts Open, regardless of input
    finally:
        db_session.query(RiskAssessment).filter(RiskAssessment.RiskAssessmentId == risk_id).delete()
        db_session.commit()


# --- IDOR / ID-guessing sweep ----------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        f"/api/properties/{_NONEXISTENT_ID}",
        f"/api/units/{_NONEXISTENT_ID}",
        f"/api/inspection-templates/{_NONEXISTENT_ID}",
        f"/api/inspections/{_NONEXISTENT_ID}",
        f"/api/maintenance-issues/{_NONEXISTENT_ID}",
        f"/api/risk-assessments/{_NONEXISTENT_ID}",
        f"/api/meter-readings/{_NONEXISTENT_ID}",
        f"/api/cleaning-inspections/{_NONEXISTENT_ID}",
        f"/api/vacant-unit-inspections/{_NONEXISTENT_ID}",
        f"/api/media/{_NONEXISTENT_ID}",
    ],
)
def test_nonexistent_id_returns_404_not_500(client: TestClient, northgate_admin, path: str) -> None:
    """A guessed/incremented ID for a record that simply doesn't exist must 404 cleanly on every
    module's detail endpoint, not leak a 500/stack trace that would confirm the ID space or
    reveal internals to someone probing for valid IDs."""
    response = client.get(path, headers=auth_headers(client, northgate_admin.Email))
    assert response.status_code == 404


def test_negative_id_returns_404_or_422_not_500(client: TestClient, northgate_admin) -> None:
    response = client.get("/api/properties/-1", headers=auth_headers(client, northgate_admin.Email))
    assert response.status_code in (404, 422)


def test_non_numeric_id_returns_422_not_500(client: TestClient, northgate_admin) -> None:
    response = client.get(
        "/api/properties/'; DROP TABLE Properties; --", headers=auth_headers(client, northgate_admin.Email)
    )
    assert response.status_code == 422


# --- injection-style payload safety -----------------------------------------------------------


def test_sql_injection_style_search_query_is_safe(client: TestClient, northgate_admin) -> None:
    """SQLAlchemy's parameterized queries should treat this as a literal search string, not
    executable SQL - proven by a clean 200 with no matches, not a 500 or a full table dump."""
    headers = auth_headers(client, northgate_admin.Email)
    payload = "' OR '1'='1"
    response = client.get("/api/properties", params={"search": payload}, headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 0

    response2 = client.get(
        "/api/properties", params={"search": "x'; DROP TABLE Properties; --"}, headers=headers
    )
    assert response2.status_code == 200
    # Prove the table really does still exist and is queryable afterward.
    sanity = client.get("/api/properties", headers=headers)
    assert sanity.status_code == 200
    assert sanity.json()["total"] > 0


def test_script_payload_in_title_is_stored_and_returned_verbatim(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    """Confirms the API layer neither crashes on nor silently mangles a script-injection-style
    payload - it's stored/returned as inert data. Output-encoding at render time is the
    frontend's job (React escapes by default), not something the API should second-guess by
    mutating stored content."""
    headers = auth_headers(client, northgate_admin.Email)
    payload_title = "<script>alert('xss')</script>"
    create = client.post(
        "/api/maintenance-issues",
        json={"PropertyId": northgate_property_id, "Title": payload_title, "Category": "Plumbing"},
        headers=headers,
    )
    assert create.status_code == 201
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        assert create.json()["Title"] == payload_title
        fetched = client.get(f"/api/maintenance-issues/{issue_id}", headers=headers)
        assert fetched.json()["Title"] == payload_title
    finally:
        _delete_maintenance_issue(db_session, issue_id)


# --- upload abuse ------------------------------------------------------------------------------


def test_oversized_image_upload_rejected_and_file_not_orphaned(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    """MEDIA_MAX_IMAGE_SIZE_BYTES (15MB, app/core/config.py) is enforced in
    media_service.upload_media but had no test at all before this - the size check existed
    purely on trust. Also confirms the documented cleanup behavior: the oversized file is
    written to disk (UploadFile can't be size-checked before reading), then deleted immediately
    on rejection, never left orphaned."""
    headers = auth_headers(client, northgate_admin.Email)
    oversized = b"\xff\xd8\xff\xe0" + (b"\x00" * (settings.MEDIA_MAX_IMAGE_SIZE_BYTES + 1))

    before_count = db_session.query(MediaFile).filter(MediaFile.EntityId == northgate_property_id).count()

    response = client.post(
        "/api/media",
        data={"entity_type": "Property", "entity_id": northgate_property_id},
        files={"file": ("huge.jpg", oversized, "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 422

    after_count = db_session.query(MediaFile).filter(MediaFile.EntityId == northgate_property_id).count()
    assert after_count == before_count  # no orphaned row

    upload_dir = Path(settings.MEDIA_UPLOAD_DIR) / "Property" / str(northgate_property_id)
    if upload_dir.exists():
        leftover = list(upload_dir.glob("*"))
        assert leftover == []  # no orphaned file left on disk


def test_zero_byte_file_upload_is_accepted_or_cleanly_rejected(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    """Not a documented rule either way - this just proves a degenerate empty upload doesn't
    crash the server, whichever way the app chooses to handle it."""
    headers = auth_headers(client, northgate_admin.Email)
    response = client.post(
        "/api/media",
        data={"entity_type": "Property", "entity_id": northgate_property_id},
        files={"file": ("empty.jpg", b"", "image/jpeg")},
        headers=headers,
    )
    assert response.status_code in (201, 422)
    if response.status_code == 201:
        media_id = response.json()["MediaFileId"]
        media_file = db_session.get(MediaFile, media_id)
        file_path = Path(settings.MEDIA_UPLOAD_DIR) / media_file.StorageKey
        file_path.unlink(missing_ok=True)
        db_session.delete(media_file)
        db_session.commit()


# --- pagination bounds ---------------------------------------------------------------------


@pytest.mark.parametrize("params", [{"page": 0}, {"page": -1}, {"page_size": 0}, {"page_size": 10000}])
def test_pagination_out_of_bounds_rejected(client: TestClient, northgate_admin, params: dict) -> None:
    response = client.get("/api/properties", params=params, headers=auth_headers(client, northgate_admin.Email))
    assert response.status_code == 422


# --- genuine concurrency (not just sequential) ------------------------------------------------


def _delete_inspection(db_session: Session, inspection_id: int) -> None:
    db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection_id).delete()
    db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).delete()
    db_session.commit()


def test_concurrent_double_submit_only_one_request_succeeds(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    """test_inspections.py's test_submitting_twice_returns_409 proves the SEQUENTIAL case (submit,
    wait for the response, submit again). That doesn't prove anything about two requests that
    are genuinely in flight at the same time - if the Status=='Submitted' check and the update
    aren't atomic against each other, two near-simultaneous requests could both read
    'InProgress' before either commits, and both succeed. Fires two real threads at the same
    submit endpoint to check for exactly that race, not just the easy sequential case."""
    headers = auth_headers(client, northgate_inspector.Email)
    start = client.post(
        "/api/inspections",
        json={"PropertyId": northgate_property_id, "InspectionTemplateId": template_id},
        headers=headers,
    )
    assert start.status_code == 201
    inspection_id = start.json()["InspectionId"]
    all_responses = [r for s in start.json()["Sections"] for r in s["Responses"]]

    try:
        for r in all_responses:
            client.patch(
                f"/api/inspections/{inspection_id}/responses/{r['InspectionResponseId']}",
                json={"IsNotApplicable": True},
                headers=headers,
            )

        results: list[int] = []
        results_lock = threading.Lock()

        def _submit() -> None:
            resp = client.post(f"/api/inspections/{inspection_id}/submit", headers=headers)
            with results_lock:
                results.append(resp.status_code)

        threads = [threading.Thread(target=_submit) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count(200) == 1, f"expected exactly one 200 among concurrent submits, got {results}"
        assert all(code in (200, 409) for code in results)
    finally:
        _delete_inspection(db_session, inspection_id)
