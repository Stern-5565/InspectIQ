"""Dashboard API tests - same conventions as test_risk.py/test_maintenance.py (real DB, no
mocks, explicit cleanup). No new authorization design to test here (view = any company member,
same as every other module's read side) - the real risk in this phase is the aggregate SQL
itself, so these tests focus on the numbers actually moving when real data is created, not just
that the endpoint returns 200.
"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.maintenance_issue import MaintenanceIssue
from app.models.maintenance_update import MaintenanceUpdate
from app.models.property import Property
from app.models.risk_assessment import RiskAssessment
from tests.conftest import auth_headers, delete_user, make_user


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.dash.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_maintenance(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.dash.worker.tmp@example.com",
        role_name="Maintenance",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.dash.bsadmin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_property_id(db_session: Session) -> int:
    return db_session.execute(
        select(Property.PropertyId).where(Property.PropertyName == "15 High Road")
    ).scalar_one()


def _delete_issue(db_session: Session, issue_id: int) -> None:
    db_session.query(MaintenanceUpdate).filter(MaintenanceUpdate.MaintenanceIssueId == issue_id).delete()
    db_session.query(MaintenanceIssue).filter(MaintenanceIssue.MaintenanceIssueId == issue_id).delete()
    db_session.commit()


def _delete_risk_assessment(db_session: Session, risk_assessment_id: int) -> None:
    db_session.query(RiskAssessment).filter(RiskAssessment.RiskAssessmentId == risk_assessment_id).delete()
    db_session.commit()


def test_dashboard_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/dashboard")
    assert response.status_code == 401


def test_dashboard_view_open_to_maintenance_role(
    client: TestClient, northgate_maintenance
) -> None:
    """Maintenance is the most restricted role everywhere else in this project (blocked from
    creating Risk/most Maintenance mutations) - confirming it can still view the dashboard is
    the real check that "view = any company member" actually holds here too."""
    headers = auth_headers(client, northgate_maintenance.Email)
    response = client.get("/api/dashboard", headers=headers)

    assert response.status_code == 200
    body = response.json()
    for section in ("Inspections", "Maintenance", "Risks", "Cleaning", "Properties", "RecentActivity"):
        assert section in body
    assert set(body["RecentActivity"].keys()) == {"Inspections", "MaintenanceIssues", "RiskAssessments"}


def test_dashboard_reflects_new_urgent_maintenance_issue(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    before = client.get("/api/dashboard", headers=headers).json()

    create = client.post(
        "/api/maintenance-issues",
        json={
            "PropertyId": northgate_property_id,
            "Title": "Dashboard test - burst pipe",
            "Category": "Plumbing",
            "Priority": "Urgent",
        },
        headers=headers,
    )
    assert create.status_code == 201
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        after = client.get("/api/dashboard", headers=headers).json()

        assert after["Maintenance"]["OpenCount"] == before["Maintenance"]["OpenCount"] + 1
        assert after["Maintenance"]["UrgentOrEmergency"] == before["Maintenance"]["UrgentOrEmergency"] + 1

        recent_ids = {item["MaintenanceIssueId"] for item in after["RecentActivity"]["MaintenanceIssues"]}
        assert issue_id in recent_ids
    finally:
        _delete_issue(db_session, issue_id)


def test_dashboard_reflects_new_critical_risk(
    client: TestClient, db_session: Session, northgate_admin, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_admin.Email)
    before = client.get("/api/dashboard", headers=headers).json()

    create = client.post(
        "/api/risk-assessments",
        json={
            "PropertyId": northgate_property_id,
            "Hazard": "Dashboard test - exposed wiring",
            "Likelihood": 5,
            "Severity": 5,
        },
        headers=headers,
    )
    assert create.status_code == 201
    body = create.json()
    assert body["RiskLevel"] == "Critical"
    risk_id = body["RiskAssessmentId"]

    try:
        after = client.get("/api/dashboard", headers=headers).json()

        assert after["Risks"]["CriticalCount"] == before["Risks"]["CriticalCount"] + 1
        assert after["Risks"]["OutstandingCount"] == before["Risks"]["OutstandingCount"] + 1

        recent_ids = {item["RiskAssessmentId"] for item in after["RecentActivity"]["RiskAssessments"]}
        assert risk_id in recent_ids
    finally:
        _delete_risk_assessment(db_session, risk_id)


def test_dashboard_isolates_by_company(
    client: TestClient,
    db_session: Session,
    northgate_admin,
    bright_spaces_admin,
    northgate_property_id: int,
) -> None:
    northgate_headers = auth_headers(client, northgate_admin.Email)
    create = client.post(
        "/api/maintenance-issues",
        json={
            "PropertyId": northgate_property_id,
            "Title": "Dashboard test - isolation check",
            "Category": "Other",
            "Priority": "Urgent",
        },
        headers=northgate_headers,
    )
    assert create.status_code == 201
    issue_id = create.json()["MaintenanceIssueId"]

    try:
        bright_spaces_headers = auth_headers(client, bright_spaces_admin.Email)
        other_company_dashboard = client.get("/api/dashboard", headers=bright_spaces_headers).json()

        recent_ids = {
            item["MaintenanceIssueId"] for item in other_company_dashboard["RecentActivity"]["MaintenanceIssues"]
        }
        assert issue_id not in recent_ids
    finally:
        _delete_issue(db_session, issue_id)
