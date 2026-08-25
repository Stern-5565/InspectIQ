"""
Inspection engine tests - real DB, no mocks. Inspections/InspectionResponses have no
soft-delete-only trigger (unlike InspectionTemplates/Sections/Questions), so test cleanup is a
plain hard delete, no disable-trigger dance needed.
"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.inspection_response import InspectionResponse
from app.models.inspection_template import InspectionTemplate
from app.models.property import Property
from tests.conftest import auth_headers, delete_user, make_user


@pytest.fixture
def northgate_inspector(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.inspections.inspector.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector2(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.inspections.inspector2.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_manager(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.inspections.manager.tmp@example.com",
        role_name="Manager",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_maintenance(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.inspections.maintenance.tmp@example.com",
        role_name="Maintenance",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.inspections.bsadmin.tmp@example.com",
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


def _delete_inspection(db_session: Session, inspection_id: int) -> None:
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


# --- start -----------------------------------------------------------------------------

def test_start_inspection_creates_snapshot_responses_in_template_order(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)

    try:
        assert body["Status"] == "InProgress"
        assert body["TemplateVersionUsed"] == 1
        assert body["CompletionPercentage"] == 0.0
        assert len(body["Sections"]) == 21
        assert body["Sections"][0]["SectionName"] == "Property Access"
        assert body["Sections"][0]["Responses"][0]["QuestionTextSnapshot"] == "Was access available?"
        total_responses = sum(len(s["Responses"]) for s in body["Sections"])
        assert total_responses == 102
    finally:
        _delete_inspection(db_session, body["InspectionId"])


def test_start_inspection_for_property_in_another_company_returns_404(
    client: TestClient, bright_spaces_admin, northgate_property_id: int, template_id: int
) -> None:
    response = client.post(
        "/api/inspections",
        json={"PropertyId": northgate_property_id, "InspectionTemplateId": template_id},
        headers=auth_headers(client, bright_spaces_admin.Email),
    )
    assert response.status_code == 404


def test_start_inspection_as_maintenance_role_returns_403(
    client: TestClient, northgate_maintenance, northgate_property_id: int, template_id: int
) -> None:
    response = client.post(
        "/api/inspections",
        json={"PropertyId": northgate_property_id, "InspectionTemplateId": template_id},
        headers=auth_headers(client, northgate_maintenance.Email),
    )
    assert response.status_code == 403


# --- answering ---------------------------------------------------------------------------

def test_update_response_sets_answer_and_notes(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)
    first_response = body["Sections"][0]["Responses"][0]  # "Was access available?" - YesNo

    try:
        response = client.patch(
            f"/api/inspections/{body['InspectionId']}/responses/{first_response['InspectionResponseId']}",
            json={"AnswerText": "Yes", "Notes": "Key safe worked fine"},
            headers=headers,
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["AnswerText"] == "Yes"
        assert updated["Notes"] == "Key safe worked fine"
        assert updated["UpdatedAt"] is not None
    finally:
        _delete_inspection(db_session, body["InspectionId"])


def test_update_response_rejects_invalid_yesno_value(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)
    first_response = body["Sections"][0]["Responses"][0]

    try:
        response = client.patch(
            f"/api/inspections/{body['InspectionId']}/responses/{first_response['InspectionResponseId']}",
            json={"AnswerText": "Maybe"},
            headers=headers,
        )
        assert response.status_code == 422
    finally:
        _delete_inspection(db_session, body["InspectionId"])


def test_update_response_with_answer_number_normalizes_answer_text(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    """The Electricity Meter section's first question is a MeterReading type - setting
    AnswerNumber should populate the canonical AnswerText too (docs/DATABASE.md §9.4)."""
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)
    meter_section = next(s for s in body["Sections"] if s["SectionName"] == "Electricity Meter")
    meter_response = meter_section["Responses"][0]

    try:
        response = client.patch(
            f"/api/inspections/{body['InspectionId']}/responses/{meter_response['InspectionResponseId']}",
            json={"AnswerNumber": "18294.6"},
            headers=headers,
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["AnswerNumber"] == "18294.6000" or float(updated["AnswerNumber"]) == 18294.6
        assert updated["AnswerText"] == "18294.6"
    finally:
        _delete_inspection(db_session, body["InspectionId"])


def test_update_response_by_a_different_inspector_returns_403(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_inspector2,
    northgate_property_id: int,
    template_id: int,
) -> None:
    """An Inspector who isn't the one assigned to this inspection must not be able to edit
    it, even though they share the same role at the same company - deliberately stricter than
    Properties' "any company member can view/any Admin+Manager can mutate" pattern."""
    owner_headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, owner_headers, northgate_property_id, template_id)
    first_response = body["Sections"][0]["Responses"][0]

    try:
        other_headers = auth_headers(client, northgate_inspector2.Email)
        response = client.patch(
            f"/api/inspections/{body['InspectionId']}/responses/{first_response['InspectionResponseId']}",
            json={"AnswerText": "Yes"},
            headers=other_headers,
        )
        assert response.status_code == 403
    finally:
        _delete_inspection(db_session, body["InspectionId"])


def test_update_response_by_a_manager_succeeds_even_though_not_the_assigned_inspector(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_manager,
    northgate_property_id: int,
    template_id: int,
) -> None:
    owner_headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, owner_headers, northgate_property_id, template_id)
    first_response = body["Sections"][0]["Responses"][0]

    try:
        manager_headers = auth_headers(client, northgate_manager.Email)
        response = client.patch(
            f"/api/inspections/{body['InspectionId']}/responses/{first_response['InspectionResponseId']}",
            json={"AnswerText": "Yes"},
            headers=manager_headers,
        )
        assert response.status_code == 200
    finally:
        _delete_inspection(db_session, body["InspectionId"])


# --- completion percentage -----------------------------------------------------------------

def test_completion_percentage_reflects_answered_and_na_responses(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)
    all_responses = [r for section in body["Sections"] for r in section["Responses"]]
    assert len(all_responses) == 102

    try:
        # Answer 10, mark 5 as not applicable - completion should reflect exactly 15/102.
        for r in all_responses[:10]:
            client.patch(
                f"/api/inspections/{body['InspectionId']}/responses/{r['InspectionResponseId']}",
                json={"AnswerText": "Yes"},
                headers=headers,
            )
        for r in all_responses[10:15]:
            client.patch(
                f"/api/inspections/{body['InspectionId']}/responses/{r['InspectionResponseId']}",
                json={"IsNotApplicable": True},
                headers=headers,
            )

        detail = client.get(f"/api/inspections/{body['InspectionId']}", headers=headers).json()
        expected = round(15 / 102 * 100, 1)
        assert detail["CompletionPercentage"] == expected
    finally:
        _delete_inspection(db_session, body["InspectionId"])


# --- submit ------------------------------------------------------------------------------

def test_submit_fails_with_unanswered_mandatory_questions(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)

    try:
        response = client.post(f"/api/inspections/{body['InspectionId']}/submit", headers=headers)
        assert response.status_code == 422
        assert "mandatory" in response.json()["detail"].lower()
    finally:
        _delete_inspection(db_session, body["InspectionId"])


def test_submit_succeeds_when_all_responses_marked_not_applicable(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)
    all_responses = [r for section in body["Sections"] for r in section["Responses"]]

    try:
        for r in all_responses:
            client.patch(
                f"/api/inspections/{body['InspectionId']}/responses/{r['InspectionResponseId']}",
                json={"IsNotApplicable": True},
                headers=headers,
            )

        response = client.post(f"/api/inspections/{body['InspectionId']}/submit", headers=headers)
        assert response.status_code == 200
        submitted = response.json()
        assert submitted["Status"] == "Submitted"
        assert submitted["SubmittedAt"] is not None
        assert submitted["CompletionPercentage"] == 100.0
    finally:
        _delete_inspection(db_session, body["InspectionId"])


def test_submitting_twice_returns_409(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)
    all_responses = [r for section in body["Sections"] for r in section["Responses"]]

    try:
        for r in all_responses:
            client.patch(
                f"/api/inspections/{body['InspectionId']}/responses/{r['InspectionResponseId']}",
                json={"IsNotApplicable": True},
                headers=headers,
            )
        first = client.post(f"/api/inspections/{body['InspectionId']}/submit", headers=headers)
        assert first.status_code == 200

        second = client.post(f"/api/inspections/{body['InspectionId']}/submit", headers=headers)
        assert second.status_code == 409
    finally:
        _delete_inspection(db_session, body["InspectionId"])


def test_cannot_edit_a_response_after_submission(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)
    all_responses = [r for section in body["Sections"] for r in section["Responses"]]

    try:
        for r in all_responses:
            client.patch(
                f"/api/inspections/{body['InspectionId']}/responses/{r['InspectionResponseId']}",
                json={"IsNotApplicable": True},
                headers=headers,
            )
        client.post(f"/api/inspections/{body['InspectionId']}/submit", headers=headers)

        response = client.patch(
            f"/api/inspections/{body['InspectionId']}/responses/{all_responses[0]['InspectionResponseId']}",
            json={"IsNotApplicable": False, "AnswerText": "Yes"},
            headers=headers,
        )
        assert response.status_code == 409
    finally:
        _delete_inspection(db_session, body["InspectionId"])


# --- update inspection (summary fields) -------------------------------------------------------

def test_update_inspection_sets_summary_fields(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)

    try:
        response = client.patch(
            f"/api/inspections/{body['InspectionId']}",
            json={
                "GeneralNotes": "Quiet visit, tenant was cooperative.",
                "OverallCondition": "Satisfactory",
                "OverallRiskRating": "Low",
            },
            headers=headers,
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["GeneralNotes"] == "Quiet visit, tenant was cooperative."
        assert updated["OverallCondition"] == "Satisfactory"
        assert updated["OverallRiskRating"] == "Low"

        # Re-fetch confirms it's actually persisted, not just echoed back.
        refetched = client.get(f"/api/inspections/{body['InspectionId']}", headers=headers)
        assert refetched.json()["OverallCondition"] == "Satisfactory"
    finally:
        _delete_inspection(db_session, body["InspectionId"])


def test_update_inspection_rejects_invalid_overall_condition(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)

    try:
        response = client.patch(
            f"/api/inspections/{body['InspectionId']}",
            json={"OverallCondition": "NotARealValue"},
            headers=headers,
        )
        assert response.status_code == 422
    finally:
        _delete_inspection(db_session, body["InspectionId"])


def test_update_inspection_by_a_different_inspector_returns_403(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_inspector2,
    northgate_property_id: int,
    template_id: int,
) -> None:
    owner_headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, owner_headers, northgate_property_id, template_id)

    try:
        other_headers = auth_headers(client, northgate_inspector2.Email)
        response = client.patch(
            f"/api/inspections/{body['InspectionId']}",
            json={"GeneralNotes": "Should not be allowed."},
            headers=other_headers,
        )
        assert response.status_code == 403
    finally:
        _delete_inspection(db_session, body["InspectionId"])


def test_cannot_update_inspection_summary_after_submission(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)
    all_responses = [r for section in body["Sections"] for r in section["Responses"]]

    try:
        for r in all_responses:
            client.patch(
                f"/api/inspections/{body['InspectionId']}/responses/{r['InspectionResponseId']}",
                json={"IsNotApplicable": True},
                headers=headers,
            )
        client.post(f"/api/inspections/{body['InspectionId']}/submit", headers=headers)

        response = client.patch(
            f"/api/inspections/{body['InspectionId']}",
            json={"GeneralNotes": "Too late."},
            headers=headers,
        )
        assert response.status_code == 409
    finally:
        _delete_inspection(db_session, body["InspectionId"])


# --- isolation -----------------------------------------------------------------------------

def test_get_inspection_belonging_to_another_company_returns_404(
    client: TestClient, db_session: Session, northgate_inspector, bright_spaces_admin, northgate_property_id: int, template_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    body = _start_inspection(client, headers, northgate_property_id, template_id)

    try:
        response = client.get(
            f"/api/inspections/{body['InspectionId']}", headers=auth_headers(client, bright_spaces_admin.Email)
        )
        assert response.status_code == 404
    finally:
        _delete_inspection(db_session, body["InspectionId"])
