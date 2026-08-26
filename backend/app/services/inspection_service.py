from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.inspection import Inspection
from app.models.inspection_response import InspectionResponse
from app.models.user import User
from app.repositories import inspection_repository as repo
from app.repositories import inspection_response_repository as response_repo
from app.schemas.inspection import InspectionCreate, InspectionResponseUpdate, InspectionUpdate
from app.security import roles
from app.services import inspection_template_service, property_service

_VALID_YESNO = {"Yes", "No"}
_VALID_PASSFAIL = {"Pass", "Fail"}
_MANAGE_ROLES = {roles.ADMINISTRATOR, roles.MANAGER}


def _is_answered(response: InspectionResponse) -> bool:
    return response.IsNotApplicable or bool(response.AnswerText and response.AnswerText.strip())


def calculate_completion_percentage(responses: list[InspectionResponse]) -> float:
    if not responses:
        return 0.0
    answered = sum(1 for r in responses if _is_answered(r))
    return round(answered / len(responses) * 100, 1)


def ensure_can_edit(current_user: User, inspection: Inspection) -> None:
    """Response edits and submission are restricted to the inspection's own assigned
    inspector, or an Administrator/Manager - deliberately narrower than Properties/Templates'
    "any company member can view, Admin/Manager can mutate" pattern. Unlike a property, an
    in-progress inspection is one specific person's active work; another Inspector at the same
    company shouldn't be able to silently alter it just by sharing the Inspector role. Viewing
    (GET) has no such restriction - any authenticated company member can see any inspection,
    same as everything else in this project so far.

    Public (not module-private) because app/services/media_service.py reuses it for the same
    "who can attach evidence to this inspection" question - Phase 9."""
    is_assigned_inspector = current_user.UserId == inspection.InspectorUserId
    user_role_names = {role.RoleName for role in current_user.roles}
    is_manager_or_admin = bool(user_role_names.intersection(_MANAGE_ROLES))
    if not (is_assigned_inspector or is_manager_or_admin):
        raise ForbiddenError("Only the assigned inspector, a Manager, or an Administrator can modify this inspection.")


def start_inspection(db: Session, current_user: User, payload: InspectionCreate) -> Inspection:
    # Both raise NotFoundError (not ForbiddenError) if the property/template isn't visible to
    # this company - same isolation principle applied consistently, reused rather than
    # reimplemented.
    property_ = property_service.get_property(db, current_user, payload.PropertyId)
    template = inspection_template_service.get_template(db, current_user, payload.InspectionTemplateId)

    inspection = Inspection(
        PropertyId=property_.PropertyId,
        InspectorUserId=current_user.UserId,
        InspectionTemplateId=template.InspectionTemplateId,
        TemplateVersionUsed=template.Version,
        InspectionType=payload.InspectionType,
        InspectionDate=payload.InspectionDate or date.today(),
        StartedAt=datetime.now(timezone.utc),
        Status="InProgress",
    )
    inspection = repo.create_inspection(db, inspection)

    # Snapshot every active section/question into a frozen InspectionResponse row, in
    # template SortOrder (both relationships carry order_by=...SortOrder - see
    # app/models/inspection_template.py). Inactive (soft-deleted) sections/questions are
    # skipped - they're no longer part of the checklist for a NEW inspection starting now,
    # even though old inspections' existing responses keep referencing them fine via FK.
    responses = [
        InspectionResponse(
            InspectionId=inspection.InspectionId,
            InspectionQuestionId=question.InspectionQuestionId,
            QuestionTextSnapshot=question.QuestionText,
            SectionNameSnapshot=section.SectionName,
            AnswerTypeSnapshot=question.AnswerType,
        )
        for section in template.sections
        if section.IsActive
        for question in section.questions
        if question.IsActive
    ]
    response_repo.create_responses_bulk(db, responses)

    return repo.get_inspection_by_id(db, current_user.CompanyId, inspection.InspectionId)


def list_inspections(
    db: Session,
    current_user: User,
    *,
    page: int,
    page_size: int,
    property_id: int | None = None,
    status: str | None = None,
    inspector_user_id: int | None = None,
) -> tuple[list[Inspection], int]:
    return repo.list_inspections(
        db,
        current_user.CompanyId,
        page=page,
        page_size=page_size,
        property_id=property_id,
        status=status,
        inspector_user_id=inspector_user_id,
    )


def get_inspection(db: Session, current_user: User, inspection_id: int) -> Inspection:
    inspection = repo.get_inspection_by_id(db, current_user.CompanyId, inspection_id)
    if inspection is None:
        raise NotFoundError("Inspection not found.")
    return inspection


def update_inspection(
    db: Session, current_user: User, inspection_id: int, payload: InspectionUpdate
) -> Inspection:
    """Sets the inspection-level summary fields (GeneralNotes/OverallCondition/
    OverallRiskRating) - added for the Inspection Review screen (Prompt 17). Same
    authorization and post-submission immutability rules as update_response: only the
    assigned inspector or an Administrator/Manager, and never after Status becomes
    "Submitted" (reports must represent the inspection exactly as it existed at submission,
    scope §18)."""
    inspection = get_inspection(db, current_user, inspection_id)
    ensure_can_edit(current_user, inspection)

    if inspection.Status == "Submitted":
        raise ConflictError("Cannot modify a submitted inspection.")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(inspection, field, value.value if isinstance(value, Enum) else value)

    return repo.save_inspection(db, inspection)


def _normalize_answer(response: InspectionResponse, payload: InspectionResponseUpdate) -> dict:
    """Validates binary answer types strictly (a typo in Yes/No or Pass/Fail is meaningless,
    not a matter of taste) and keeps AnswerText - the canonical display value,
    docs/DATABASE.md §9.4 - in sync when AnswerNumber/AnswerDate is what the caller actually
    sent. Condition/Text answer types stay freeform; no DB constraint governs them, so no
    app-layer one is invented here either."""
    data = payload.model_dump(exclude_unset=True)
    answer_type = response.AnswerTypeSnapshot

    if data.get("AnswerText") is not None:
        if answer_type == "YesNo" and data["AnswerText"] not in _VALID_YESNO:
            raise ValidationError("AnswerText for a YesNo question must be 'Yes' or 'No'.")
        if answer_type == "PassFail" and data["AnswerText"] not in _VALID_PASSFAIL:
            raise ValidationError("AnswerText for a PassFail question must be 'Pass' or 'Fail'.")

    if data.get("AnswerNumber") is not None:
        data["AnswerText"] = str(data["AnswerNumber"])
    if data.get("AnswerDate") is not None:
        data["AnswerText"] = data["AnswerDate"].isoformat()

    return data


def update_response(
    db: Session, current_user: User, inspection_id: int, response_id: int, payload: InspectionResponseUpdate
) -> InspectionResponse:
    inspection = get_inspection(db, current_user, inspection_id)
    ensure_can_edit(current_user, inspection)

    if inspection.Status == "Submitted":
        # Reports must represent the inspection exactly as it existed when submitted (scope
        # §18) - responses become immutable through the API the moment that happens. Nothing
        # at the DB level blocks this (unlike InspectionTemplates' hard-delete trigger), so
        # this check is the only thing enforcing it.
        raise ConflictError("Cannot modify responses on a submitted inspection.")

    response = response_repo.get_response_within_inspection(db, inspection_id, response_id)
    if response is None:
        raise NotFoundError("Inspection response not found.")

    for field, value in _normalize_answer(response, payload).items():
        setattr(response, field, value)
    response.UpdatedAt = datetime.now(timezone.utc)

    return response_repo.save_response(db, response)


def submit_inspection(db: Session, current_user: User, inspection_id: int) -> Inspection:
    inspection = get_inspection(db, current_user, inspection_id)
    ensure_can_edit(current_user, inspection)

    if inspection.Status == "Submitted":
        raise ConflictError("Inspection has already been submitted.")

    unanswered = response_repo.list_unanswered_mandatory(db, inspection_id)
    if unanswered:
        preview = ", ".join(r.QuestionTextSnapshot for r in unanswered[:5])
        remaining = len(unanswered) - 5
        if remaining > 0:
            preview += f", and {remaining} more"
        raise ValidationError(
            f"Cannot submit: {len(unanswered)} mandatory question(s) not yet answered ({preview})."
        )

    # The Status=='Submitted' check above is a fast, friendly early-exit for the ordinary
    # sequential case - it is NOT what makes double-submission safe. The actual guarantee is
    # this atomic conditional UPDATE (repo.submit_inspection_if_in_progress): two submit
    # requests genuinely in flight at once can both pass the check above (both still see
    # InProgress), but only one of them can win the UPDATE...WHERE Status != 'Submitted' - SQL
    # Server's row lock forces the second to wait, then re-evaluate against the now-committed
    # row and affect zero rows. Found by a real concurrent-thread test, not by inspection - see
    # docs/AI_MEMORY.md's Phase 18 entry.
    now = datetime.now(timezone.utc)
    if not repo.submit_inspection_if_in_progress(db, inspection_id, submitted_at=now):
        raise ConflictError("Inspection has already been submitted.")

    db.refresh(inspection)
    return inspection
