"""Communal Cleaning Grading (Phase 11, scope §16).

A simpler authorization shape than Maintenance (Phase 10), and deliberately so - see
`app/schemas/cleaning.py`'s `CleaningInspectionUpdate` docstring for the scope-level reason
(no audit-trail requirement here, unlike §18's Maintenance History). Two tiers, not three:

- CleaningAreas (per-property configuration, like a mini Property field): any company member
  views, Administrator/Manager creates/edits - gated at the ROUTE level, identical to
  Properties/Units themselves. This is property configuration, not day-to-day inspection work.
- CleaningInspections (grading records, always attached to a real Inspection - scope's own
  table design makes `InspectionId` NOT NULL): any company member views; create/update reuses
  `inspection_service.ensure_can_edit` in full - the inspection's own assigned inspector, or
  Administrator/Manager. Unlike MaintenanceIssue, there's no independent "assignee can edit"
  carve-out here: `AssignedUserId` on a CleaningInspection names who should DO the cleaning
  (there's no "Cleaner" role in this system - scope's 5 roles don't include one), not who is
  authorized to grade or update the record. Grading a communal area is part of conducting the
  Inspection itself, exactly like answering a checklist question (Phase 8) - so it follows that
  module's authorization line, not Maintenance's separate-workflow line. Also locked once the
  parent Inspection is Submitted, the same 409 immutability rule InspectionResponses use.
"""
from typing import Any
from enum import Enum

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.cleaning_area import CleaningArea
from app.models.cleaning_inspection import CleaningInspection
from app.models.property import Property
from app.models.user import User
from app.repositories import cleaning_repository as repo
from app.repositories import user_repository
from app.schemas.cleaning import (
    CleaningAreaCreate,
    CleaningAreaUpdate,
    CleaningInspectionCreate,
    CleaningInspectionUpdate,
)
from app.services import inspection_service, property_service

# scope §16's own suggested minimal set (docs/DATABASE.md §10 "Possible Problems" #5), not the
# full 10-value list - a company refines/adds the rest itself via the CleaningAreas API. Kept as
# (AreaName, AreaType) pairs rather than deriving AreaName from AreaType, since AreaName is
# free text a company might localize/rename later independently of the fixed AreaType enum.
_DEFAULT_AREAS = (
    ("Entrance", "Entrance"),
    ("Hallway", "Hallway"),
    ("Bin Area", "BinArea"),
)


def _to_plain(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _resolve_company_user(db: Session, current_user: User, user_id: int) -> User:
    user = user_repository.get_user_by_id(db, user_id)
    if user is None or user.CompanyId != current_user.CompanyId:
        raise NotFoundError("User not found.")
    return user


def seed_default_areas_for_property(db: Session, property_: Property) -> None:
    """Called once, immediately after a Property is created (app/services/property_service.py's
    create_property) - not exposed as its own authorized action, since it's an internal
    onboarding step for a Property that was just created by an already-authorized caller, not a
    separately requestable operation. Closes the gap docs/DATABASE.md §10 flagged: "a new
    property has zero cleaning areas until someone configures them.\""""
    areas = [
        CleaningArea(PropertyId=property_.PropertyId, AreaName=name, AreaType=area_type)
        for name, area_type in _DEFAULT_AREAS
    ]
    repo.create_areas_bulk(db, areas)


# --- Cleaning Areas ------------------------------------------------------------------------


def create_area(
    db: Session, current_user: User, property_id: int, payload: CleaningAreaCreate
) -> CleaningArea:
    property_service.get_property(db, current_user, property_id)  # 404s if not this company's
    area = CleaningArea(
        PropertyId=property_id,
        AreaName=payload.AreaName,
        AreaType=_to_plain(payload.AreaType),
    )
    return repo.create_area(db, area)


def list_areas(
    db: Session, current_user: User, property_id: int, *, include_inactive: bool = False
) -> list[CleaningArea]:
    property_service.get_property(db, current_user, property_id)
    return repo.list_areas_for_property(db, current_user.CompanyId, property_id, include_inactive=include_inactive)


def get_area(db: Session, current_user: User, area_id: int) -> CleaningArea:
    area = repo.get_area_by_id(db, current_user.CompanyId, area_id)
    if area is None:
        raise NotFoundError("Cleaning area not found.")
    return area


def update_area(db: Session, current_user: User, area_id: int, payload: CleaningAreaUpdate) -> CleaningArea:
    area = get_area(db, current_user, area_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(area, field, _to_plain(value))
    return repo.save_area(db, area)


# --- Cleaning Inspections (grading) ---------------------------------------------------------


def create_cleaning_inspection(
    db: Session, current_user: User, inspection_id: int, payload: CleaningInspectionCreate
) -> CleaningInspection:
    inspection = inspection_service.get_inspection(db, current_user, inspection_id)
    inspection_service.ensure_can_edit(current_user, inspection)
    if inspection.Status == "Submitted":
        raise ConflictError("Cannot add a cleaning grade to a submitted inspection.")

    area = get_area(db, current_user, payload.CleaningAreaId)
    if area.PropertyId != inspection.PropertyId:
        raise ValidationError("CleaningAreaId does not belong to this inspection's property.")

    assigned_user_id = None
    if payload.AssignedUserId is not None:
        assigned_user_id = _resolve_company_user(db, current_user, payload.AssignedUserId).UserId

    cleaning_inspection = CleaningInspection(
        InspectionId=inspection.InspectionId,
        CleaningAreaId=area.CleaningAreaId,
        Grade=_to_plain(payload.Grade),
        Notes=payload.Notes,
        CleaningRequired=payload.CleaningRequired,
        Urgent=payload.Urgent,
        AssignedUserId=assigned_user_id,
        DueDate=payload.DueDate,
        Status="Assigned" if assigned_user_id is not None else "Pending",
    )
    return repo.create_cleaning_inspection(db, cleaning_inspection)


def list_cleaning_inspections(
    db: Session, current_user: User, inspection_id: int
) -> list[CleaningInspection]:
    inspection_service.get_inspection(db, current_user, inspection_id)  # 404s if not visible
    return repo.list_cleaning_inspections_for_inspection(db, inspection_id)


def get_cleaning_inspection(db: Session, current_user: User, cleaning_inspection_id: int) -> CleaningInspection:
    cleaning_inspection = repo.get_cleaning_inspection_by_id(db, current_user.CompanyId, cleaning_inspection_id)
    if cleaning_inspection is None:
        raise NotFoundError("Cleaning inspection not found.")
    return cleaning_inspection


def list_cleaning_inspections_for_company(
    db: Session,
    current_user: User,
    *,
    page: int,
    page_size: int,
    property_id: int | None = None,
    grade: str | None = None,
    status: str | None = None,
) -> tuple[list, int]:
    """The standalone Cleaning module's list - see repo.list_cleaning_inspections_for_company's
    own docstring for why this didn't exist before that module needed it."""
    return repo.list_cleaning_inspections_for_company(
        db,
        current_user.CompanyId,
        page=page,
        page_size=page_size,
        property_id=property_id,
        grade=grade,
        status=status,
    )


def get_cleaning_inspection_detail(db: Session, current_user: User, cleaning_inspection_id: int):
    """The standalone Cleaning module's single-detail lookup - composes three already-existing,
    already-authorized single-object fetchers (this function's own get_cleaning_inspection,
    inspection_service.get_inspection for PropertyId, get_area for AreaName) rather than a new
    joined repository query - the list above needs a real query for pagination efficiency across
    many rows, but a single detail lookup is cheap enough as three plain calls, and reusing them
    means no isolation logic is duplicated."""
    cleaning_inspection = get_cleaning_inspection(db, current_user, cleaning_inspection_id)
    inspection = inspection_service.get_inspection(db, current_user, cleaning_inspection.InspectionId)
    area = get_area(db, current_user, cleaning_inspection.CleaningAreaId)
    return cleaning_inspection, inspection.PropertyId, area.AreaName


def update_cleaning_inspection(
    db: Session, current_user: User, cleaning_inspection_id: int, payload: CleaningInspectionUpdate
) -> CleaningInspection:
    cleaning_inspection = get_cleaning_inspection(db, current_user, cleaning_inspection_id)
    inspection = inspection_service.get_inspection(db, current_user, cleaning_inspection.InspectionId)
    inspection_service.ensure_can_edit(current_user, inspection)
    if inspection.Status == "Submitted":
        raise ConflictError("Cannot modify a cleaning grade on a submitted inspection.")

    data = payload.model_dump(exclude_unset=True)
    if "AssignedUserId" in data and data["AssignedUserId"] is not None:
        data["AssignedUserId"] = _resolve_company_user(db, current_user, data["AssignedUserId"]).UserId

    for field, value in data.items():
        setattr(cleaning_inspection, field, _to_plain(value))
    return repo.save_cleaning_inspection(db, cleaning_inspection)
