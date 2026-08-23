"""
Inspection template API tests - real DB, no mocks. The global default "Monthly Property
Inspection" template (seeded by database/seed/12_SeedInspectionTemplate.sql) is used directly
for structure-verification tests rather than creating a throwaway one, since it's stable seed
data, not something a test could corrupt (these tests only ever read it). A throwaway
company-specific template is created for the one test that needs to prove isolation, since no
company-specific template exists in seed data to test against otherwise.
"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.inspection_template import InspectionTemplate
from tests.conftest import auth_headers, delete_user, make_user


def _hard_delete_test_template(db_session: Session, template_id: int) -> None:
    """InspectionTemplates is soft-delete only - a real INSTEAD OF DELETE trigger
    (database/constraints/09_Constraints.sql) rejects a plain DELETE, by design, to protect
    real historical data. For a throwaway row created only for this test, disabling the
    trigger for one cleanup statement is the correct escape hatch (the same one used to
    originally verify the trigger itself in database/scripts/test_09_constraints_verify.sql) -
    application code must never do this, only test cleanup for rows the test itself created."""
    db_session.execute(text("DISABLE TRIGGER trg_InspectionTemplates_PreventHardDelete ON dbo.InspectionTemplates"))
    db_session.query(InspectionTemplate).filter(
        InspectionTemplate.InspectionTemplateId == template_id
    ).delete()
    db_session.execute(text("ENABLE TRIGGER trg_InspectionTemplates_PreventHardDelete ON dbo.InspectionTemplates"))
    db_session.commit()


@pytest.fixture
def northgate_user(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.templates.northgate.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_user(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.templates.brightspaces.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


def test_list_templates_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/inspection-templates")
    assert response.status_code == 401


def test_list_templates_includes_the_global_default(client: TestClient, northgate_user) -> None:
    response = client.get(
        "/api/inspection-templates", headers=auth_headers(client, northgate_user.Email)
    )

    assert response.status_code == 200
    names = {item["TemplateName"] for item in response.json()}
    assert "Monthly Property Inspection" in names
    # List view is lightweight - no nested structure.
    first = response.json()[0]
    assert "Sections" not in first


def test_get_template_returns_full_nested_structure_in_sort_order(
    client: TestClient, db_session: Session, northgate_user
) -> None:
    template_id = db_session.query(InspectionTemplate.InspectionTemplateId).filter(
        InspectionTemplate.TemplateName == "Monthly Property Inspection"
    ).scalar()

    response = client.get(
        f"/api/inspection-templates/{template_id}", headers=auth_headers(client, northgate_user.Email)
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["Sections"]) == 21
    assert body["Sections"][0]["SectionName"] == "Property Access"
    assert body["Sections"][0]["SortOrder"] == 1
    assert len(body["Sections"][0]["Questions"]) == 8
    assert body["Sections"][0]["Questions"][0]["QuestionText"] == "Was access available?"
    assert body["Sections"][0]["Questions"][0]["IsMandatory"] is True

    total_questions = sum(len(section["Questions"]) for section in body["Sections"])
    assert total_questions == 102


def test_get_nonexistent_template_returns_404(client: TestClient, northgate_user) -> None:
    response = client.get(
        "/api/inspection-templates/999999", headers=auth_headers(client, northgate_user.Email)
    )
    assert response.status_code == 404


def test_company_specific_template_is_invisible_to_another_company(
    client: TestClient, db_session: Session, northgate_user, bright_spaces_user
) -> None:
    """A company-specific (non-global) template must be isolated exactly like a Property -
    404, not 403, for anyone outside that company. No such template exists in seed data (only
    the global default), so this creates one directly to test against."""
    template = InspectionTemplate(
        CompanyId=northgate_user.CompanyId,
        TemplateName="Northgate-Only Template TMP",
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)

    try:
        northgate_response = client.get(
            f"/api/inspection-templates/{template.InspectionTemplateId}",
            headers=auth_headers(client, northgate_user.Email),
        )
        assert northgate_response.status_code == 200

        bright_spaces_response = client.get(
            f"/api/inspection-templates/{template.InspectionTemplateId}",
            headers=auth_headers(client, bright_spaces_user.Email),
        )
        assert bright_spaces_response.status_code == 404

        # And it must not leak into Bright Spaces' list view either.
        list_response = client.get(
            "/api/inspection-templates", headers=auth_headers(client, bright_spaces_user.Email)
        )
        names = {item["TemplateName"] for item in list_response.json()}
        assert "Northgate-Only Template TMP" not in names
    finally:
        _hard_delete_test_template(db_session, template.InspectionTemplateId)
