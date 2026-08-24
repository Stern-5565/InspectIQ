"""DB access only - no business rules.

No company_id parameter on most functions here - by design. Every response lookup happens
scoped to an already-authorized InspectionId (the service layer resolves and isolation-checks
the parent Inspection first, via inspection_repository.get_inspection_by_id, before ever
touching a response) - see app/services/inspection_service.py. Filtering by InspectionId here
is what actually prevents a response_id from a different inspection (or company) matching,
since InspectionResponse has no CompanyId of its own to filter on directly.

get_response_by_id_for_company is the one deliberate exception, added for Phase 9's media
attachment (app/services/media_service.py): a client attaching/viewing a photo on an
InspectionResponse only has the response_id, not its parent InspectionId, so there's no
already-authorized Inspection to scope through yet - this function has to join out to
Inspections/Properties itself to establish company isolation before the caller can look up and
isolation-check the parent Inspection the normal way.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.inspection_question import InspectionQuestion
from app.models.inspection_response import InspectionResponse
from app.models.property import Property


def create_responses_bulk(db: Session, responses: list[InspectionResponse]) -> None:
    db.add_all(responses)
    db.commit()


def get_response_within_inspection(
    db: Session, inspection_id: int, response_id: int
) -> InspectionResponse | None:
    stmt = select(InspectionResponse).where(
        InspectionResponse.InspectionId == inspection_id,
        InspectionResponse.InspectionResponseId == response_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def get_response_by_id_for_company(
    db: Session, company_id: int, response_id: int
) -> InspectionResponse | None:
    stmt = (
        select(InspectionResponse)
        .join(Inspection, Inspection.InspectionId == InspectionResponse.InspectionId)
        .join(Property, Property.PropertyId == Inspection.PropertyId)
        .where(Property.CompanyId == company_id, InspectionResponse.InspectionResponseId == response_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def save_response(db: Session, response: InspectionResponse) -> InspectionResponse:
    db.commit()
    db.refresh(response)
    return response


def list_unanswered_mandatory(db: Session, inspection_id: int) -> list[InspectionResponse]:
    """Mandatory-ness is checked against the LIVE InspectionQuestion.IsMandatory, not a
    snapshot - deliberately. Unlike response content (which must stay historically accurate
    for report rendering, hence the *Snapshot columns), a validation RULE reasonably applies
    as currently configured at submit time. If an admin loosens a question from mandatory to
    optional while an inspection is mid-flight, the inspector should get today's rules, not
    stale ones from when the inspection started. See docs/AI_MEMORY.md's 2026-08-23 Phase 8
    entry for the fuller reasoning."""
    stmt = (
        select(InspectionResponse)
        .join(InspectionQuestion, InspectionQuestion.InspectionQuestionId == InspectionResponse.InspectionQuestionId)
        .where(
            InspectionResponse.InspectionId == inspection_id,
            InspectionQuestion.IsMandatory == True,  # noqa: E712
            InspectionResponse.IsNotApplicable == False,  # noqa: E712
            (InspectionResponse.AnswerText.is_(None)) | (InspectionResponse.AnswerText == ""),
        )
    )
    return list(db.execute(stmt).scalars().all())
