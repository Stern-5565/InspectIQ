"""Risk Assessments (Phase 13, scope §19).

Two authorization tiers - re-derived from this module's own shape, not copied from either
Maintenance's three-tier or Cleaning/VacantUnit's Inspection-anchored one/two-tier pattern:

- View (list/get): any company member, consistent with every module so far.
- Create: Administrator/Manager/Inspector (gated at the ROUTE level) - identifying a hazard is
  the same kind of "flag a problem" action scope's role text already gives Inspectors for
  Maintenance ("raise maintenance"), so the same tier applies here.
- Update (ALL fields, including Status/ResponsiblePersonUserId/TargetCompletionDate, in ONE
  combined PATCH): Administrator/Manager only (gated at the ROUTE level). This is the real
  departure from Maintenance's shape, for two independent reasons, either of which would be
  sufficient on its own: (1) scope §19 describes no audit-trail requirement the way §18
  explicitly names "Maintenance History" - there's no timeline table to update piecemeal, so no
  reason to split status/notes into their own endpoints; (2) structurally, `RiskAssessment.
  InspectionId` is NULLABLE - a standalone Property-level risk register entry may have no parent
  Inspection at all, so there's no guaranteed Inspection to run `ensure_can_edit` against the
  way Cleaning/VacantUnit always can. An Admin/Manager-only route gate (identical to how
  Properties/Units/CleaningAreas gate their own mutations) is the only shape that works
  uniformly for both a standalone assessment and one linked to an inspection.

`RiskMatrixLevels` gets its own small CRUD surface too - not optional polish, scope §19 says
outright "the exact risk matrix should remain configurable." View is open to any company member
(reading rates/colors isn't sensitive); create/update are Administrator/Manager only, gated at
the route level, matching CleaningAreas' exact "per-company configuration" shape. No delete
endpoint - a matrix's bands must stay contiguous (no natural way to remove one without leaving a
score gap), and scope doesn't ask for that lifecycle management, so it isn't built.
"""
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.risk_assessment import RiskAssessment
from app.models.risk_matrix_level import RiskMatrixLevel
from app.models.user import User
from app.repositories import inspection_response_repository as response_repo
from app.repositories import risk_repository as repo
from app.repositories import user_repository
from app.schemas.risk_assessment import RiskAssessmentCreate, RiskAssessmentUpdate
from app.schemas.risk_matrix_level import RiskMatrixLevelCreate, RiskMatrixLevelUpdate
from app.services import inspection_service, maintenance_service, property_service


def _to_plain(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _resolve_company_user(db: Session, current_user: User, user_id: int) -> User:
    user = user_repository.get_user_by_id(db, user_id)
    if user is None or user.CompanyId != current_user.CompanyId:
        raise NotFoundError("User not found.")
    return user


# --- Risk Matrix Levels ----------------------------------------------------------------------


def get_risk_matrix(db: Session, current_user: User) -> list[RiskMatrixLevel]:
    return repo.get_risk_matrix_for_company(db, current_user.CompanyId)


def create_risk_matrix_level(
    db: Session, current_user: User, payload: RiskMatrixLevelCreate
) -> RiskMatrixLevel:
    if payload.MinScore > payload.MaxScore:
        raise ValidationError("MinScore cannot be greater than MaxScore.")
    level = RiskMatrixLevel(
        CompanyId=current_user.CompanyId,
        MinScore=payload.MinScore,
        MaxScore=payload.MaxScore,
        LevelName=payload.LevelName,
        SortOrder=payload.SortOrder,
        ColorHint=payload.ColorHint,
    )
    return repo.create_risk_matrix_level(db, level)


def get_risk_matrix_level(db: Session, current_user: User, risk_matrix_level_id: int) -> RiskMatrixLevel:
    level = repo.get_risk_matrix_level_by_id(db, current_user.CompanyId, risk_matrix_level_id)
    if level is None:
        raise NotFoundError("Risk matrix level not found.")
    return level


def update_risk_matrix_level(
    db: Session, current_user: User, risk_matrix_level_id: int, payload: RiskMatrixLevelUpdate
) -> RiskMatrixLevel:
    level = get_risk_matrix_level(db, current_user, risk_matrix_level_id)
    data = payload.model_dump(exclude_unset=True)
    min_score = data.get("MinScore", level.MinScore)
    max_score = data.get("MaxScore", level.MaxScore)
    if min_score > max_score:
        raise ValidationError("MinScore cannot be greater than MaxScore.")
    for field, value in data.items():
        setattr(level, field, value)
    return repo.save_risk_matrix_level(db, level)


def _resolve_risk_level(db: Session, current_user: User, score: int) -> str:
    for level in repo.get_risk_matrix_for_company(db, current_user.CompanyId):
        if level.MinScore <= score <= level.MaxScore:
            return level.LevelName
    raise ValidationError(f"No risk level is configured for a score of {score}.")


# --- Risk Assessments ------------------------------------------------------------------------


def create_risk_assessment(
    db: Session, current_user: User, payload: RiskAssessmentCreate
) -> RiskAssessment:
    inspection = None
    response = None

    if payload.InspectionResponseId is not None:
        response = response_repo.get_response_by_id_for_company(
            db, current_user.CompanyId, payload.InspectionResponseId
        )
        if response is None:
            raise NotFoundError("Inspection response not found.")
        inspection = inspection_service.get_inspection(db, current_user, response.InspectionId)
    elif payload.InspectionId is not None:
        inspection = inspection_service.get_inspection(db, current_user, payload.InspectionId)

    if inspection is not None:
        property_id = inspection.PropertyId
    else:
        if payload.PropertyId is None:
            raise ValidationError("PropertyId is required when not linked to an inspection or response.")
        property_id = property_service.get_property(db, current_user, payload.PropertyId).PropertyId

    maintenance_issue_id = None
    if payload.MaintenanceIssueId is not None:
        maintenance_issue_id = maintenance_service.get_issue(
            db, current_user, payload.MaintenanceIssueId
        ).MaintenanceIssueId

    responsible_user_id = None
    if payload.ResponsiblePersonUserId is not None:
        responsible_user_id = _resolve_company_user(db, current_user, payload.ResponsiblePersonUserId).UserId

    risk_level = _resolve_risk_level(db, current_user, payload.Likelihood * payload.Severity)

    risk_assessment = RiskAssessment(
        CompanyId=current_user.CompanyId,
        PropertyId=property_id,
        InspectionId=inspection.InspectionId if inspection is not None else None,
        InspectionResponseId=response.InspectionResponseId if response is not None else None,
        MaintenanceIssueId=maintenance_issue_id,
        Location=payload.Location,
        Hazard=payload.Hazard,
        WhoMayBeAffected=payload.WhoMayBeAffected,
        ExistingControls=payload.ExistingControls,
        Likelihood=payload.Likelihood,
        Severity=payload.Severity,
        RiskLevel=risk_level,
        AdditionalActionRequired=payload.AdditionalActionRequired,
        ResponsiblePersonUserId=responsible_user_id,
        TargetCompletionDate=payload.TargetCompletionDate,
        Notes=payload.Notes,
    )
    return repo.create_risk_assessment(db, risk_assessment)


def list_risk_assessments(
    db: Session,
    current_user: User,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    risk_level: str | None = None,
    property_id: int | None = None,
) -> tuple[list[RiskAssessment], int]:
    return repo.list_risk_assessments(
        db,
        current_user.CompanyId,
        page=page,
        page_size=page_size,
        status=status,
        risk_level=risk_level,
        property_id=property_id,
    )


def get_risk_assessment(db: Session, current_user: User, risk_assessment_id: int) -> RiskAssessment:
    risk_assessment = repo.get_risk_assessment_by_id(db, current_user.CompanyId, risk_assessment_id)
    if risk_assessment is None:
        raise NotFoundError("Risk assessment not found.")
    return risk_assessment


def update_risk_assessment(
    db: Session, current_user: User, risk_assessment_id: int, payload: RiskAssessmentUpdate
) -> RiskAssessment:
    risk_assessment = get_risk_assessment(db, current_user, risk_assessment_id)
    data = payload.model_dump(exclude_unset=True)

    if "ResponsiblePersonUserId" in data and data["ResponsiblePersonUserId"] is not None:
        data["ResponsiblePersonUserId"] = _resolve_company_user(
            db, current_user, data["ResponsiblePersonUserId"]
        ).UserId

    for field, value in data.items():
        setattr(risk_assessment, field, _to_plain(value))

    # Likelihood/Severity can change here (RiskScore itself can't - it's a real DB-computed
    # column, app/models/risk_assessment.py) - RiskLevel is re-snapshotted from the CURRENT
    # matrix whenever either changes, the same derivation create_risk_assessment uses.
    if "Likelihood" in data or "Severity" in data:
        risk_assessment.RiskLevel = _resolve_risk_level(
            db, current_user, risk_assessment.Likelihood * risk_assessment.Severity
        )

    return repo.save_risk_assessment(db, risk_assessment)
