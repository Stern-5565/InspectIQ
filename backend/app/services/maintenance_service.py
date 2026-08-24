"""Maintenance issue system (Phase 10, scope §17/§18).

Three authorization tiers, not two - a real design decision, documented per the project's
standing rule ("not every module gets the same authorization shape," `docs/AI_HANDOFF.md`):
- View (list/get/timeline): any authenticated company member - consistent with every module so
  far.
- General field edits (Title/Description/Category/Priority/DueDate/Notes) and assignment:
  Administrator/Manager only, gated at the ROUTE level (`app/api/maintenance.py`) via
  `require_roles`, the same as Properties/Units - editing an issue's core definition or deciding
  who works it is a management action.
- Status changes, notes, and photo uploads: the issue's own `AssignedUserId`, or an
  Administrator/Manager - reuses the exact `ensure_can_edit` shape Phase 8 established for
  Inspections (`inspection_service.ensure_can_edit`), because doing the actual repair work is
  one specific person's active task, not shared company data. Gated at the SERVICE level here
  (`ensure_can_edit` below) rather than by role at the route, because the assignee could hold
  any role (scope doesn't restrict assignment to the "Maintenance" role specifically) - a plain
  role-based route gate couldn't express "whoever this issue happens to be assigned to."
"""
from datetime import date
from enum import Enum
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.maintenance_issue import MaintenanceIssue
from app.models.maintenance_update import MaintenanceUpdate
from app.models.media_file import MediaFile
from app.models.user import User
from app.repositories import inspection_response_repository as response_repo
from app.repositories import maintenance_repository as repo
from app.repositories import user_repository
from app.schemas.maintenance import (
    MaintenanceAssignmentUpdate,
    MaintenanceIssueCreate,
    MaintenanceIssueUpdate,
    MaintenanceNoteCreate,
    MaintenanceStatusUpdate,
)
from app.security import roles
from app.services import inspection_service, property_service, unit_service

_MANAGE_ROLES = {roles.ADMINISTRATOR, roles.MANAGER}


def _to_plain(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _resolve_company_user(db: Session, current_user: User, user_id: int) -> User:
    user = user_repository.get_user_by_id(db, user_id)
    if user is None or user.CompanyId != current_user.CompanyId:
        # 404, not 403 - same isolation principle as every other cross-company lookup in this
        # project (docs/DATABASE.md §10.1): don't confirm a UserId exists in a company the
        # caller can't see into.
        raise NotFoundError("User not found.")
    return user


def ensure_can_edit(current_user: User, issue: MaintenanceIssue) -> None:
    is_assigned = issue.AssignedUserId is not None and current_user.UserId == issue.AssignedUserId
    user_role_names = {role.RoleName for role in current_user.roles}
    is_manager_or_admin = bool(user_role_names.intersection(_MANAGE_ROLES))
    if not (is_assigned or is_manager_or_admin):
        raise ForbiddenError(
            "Only the assigned user, a Manager, or an Administrator can modify this maintenance issue."
        )


def create_issue(db: Session, current_user: User, payload: MaintenanceIssueCreate) -> MaintenanceIssue:
    response = None
    inspection = None

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
        # The response/inspection's own Property is always the source of truth once either is
        # supplied - never a client-supplied PropertyId alongside it, which could otherwise
        # point an issue at a property the response/inspection doesn't actually belong to.
        property_id = inspection.PropertyId
    else:
        if payload.PropertyId is None:
            raise ValidationError("PropertyId is required when not linked to an inspection or response.")
        property_id = property_service.get_property(db, current_user, payload.PropertyId).PropertyId

    if payload.UnitId is not None:
        unit = unit_service.get_unit(db, current_user, payload.UnitId)
        if unit.PropertyId != property_id:
            raise ValidationError("UnitId does not belong to the resolved property.")

    location = payload.Location
    if location is None and response is not None:
        # scope §17: "automatically copying... Inspection section, Checklist item" - expressed
        # as a free-text Location fallback rather than duplicate section/question columns on
        # MaintenanceIssues, since InspectionResponseId is already a stable FK back to the
        # authoritative snapshot (docs/DATABASE.md deliberately didn't duplicate those columns).
        location = f"{response.SectionNameSnapshot} - {response.QuestionTextSnapshot}"

    assigned_user_id = None
    if payload.AssignedUserId is not None:
        assigned_user_id = _resolve_company_user(db, current_user, payload.AssignedUserId).UserId

    issue = MaintenanceIssue(
        CompanyId=current_user.CompanyId,
        PropertyId=property_id,
        UnitId=payload.UnitId,
        InspectionId=inspection.InspectionId if inspection is not None else None,
        InspectionResponseId=response.InspectionResponseId if response is not None else None,
        Title=payload.Title,
        Description=payload.Description,
        Location=location,
        Category=_to_plain(payload.Category),
        Priority=_to_plain(payload.Priority),
        Status="Assigned" if assigned_user_id is not None else "Open",
        AssignedUserId=assigned_user_id,
        ReportedByUserId=current_user.UserId,
        DueDate=payload.DueDate,
        Notes=payload.Notes,
    )
    issue = repo.create_issue(db, issue)

    repo.create_update(
        db,
        MaintenanceUpdate(
            MaintenanceIssueId=issue.MaintenanceIssueId,
            UpdateType="StatusChange",
            OldStatus=None,
            NewStatus=issue.Status,
            Comment="Issue created and assigned." if assigned_user_id is not None else "Issue created.",
            UserId=current_user.UserId,
        ),
    )
    return issue


def list_issues(
    db: Session,
    current_user: User,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    property_id: int | None = None,
    assigned_user_id: int | None = None,
) -> tuple[list[MaintenanceIssue], int]:
    return repo.list_issues(
        db,
        current_user.CompanyId,
        page=page,
        page_size=page_size,
        status=status,
        category=category,
        priority=priority,
        property_id=property_id,
        assigned_user_id=assigned_user_id,
    )


def get_issue(db: Session, current_user: User, issue_id: int) -> MaintenanceIssue:
    issue = repo.get_issue_by_id(db, current_user.CompanyId, issue_id)
    if issue is None:
        raise NotFoundError("Maintenance issue not found.")
    return issue


def list_timeline(db: Session, current_user: User, issue_id: int) -> list[MaintenanceUpdate]:
    get_issue(db, current_user, issue_id)  # 404s if not visible to this company
    return repo.list_updates_for_issue(db, issue_id)


def update_issue(
    db: Session, current_user: User, issue_id: int, payload: MaintenanceIssueUpdate
) -> MaintenanceIssue:
    issue = get_issue(db, current_user, issue_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(issue, field, _to_plain(value))
    return repo.save_issue(db, issue)


def assign_issue(
    db: Session, current_user: User, issue_id: int, payload: MaintenanceAssignmentUpdate
) -> MaintenanceIssue:
    issue = get_issue(db, current_user, issue_id)
    assignee = _resolve_company_user(db, current_user, payload.AssignedUserId)

    old_status = issue.Status
    issue.AssignedUserId = assignee.UserId
    # Auto-advances Open -> Assigned (scope §17's own status list implies assignment is what
    # that status means) but never moves a further-along issue backwards on reassignment - an
    # InProgress issue being handed to someone else stays InProgress, just records a Comment
    # noting the handoff instead of a status change.
    if issue.Status == "Open":
        issue.Status = "Assigned"
    issue = repo.save_issue(db, issue)

    status_changed = issue.Status != old_status
    repo.create_update(
        db,
        MaintenanceUpdate(
            MaintenanceIssueId=issue.MaintenanceIssueId,
            UpdateType="StatusChange" if status_changed else "Comment",
            OldStatus=old_status if status_changed else None,
            NewStatus=issue.Status if status_changed else None,
            Comment=f"Assigned to {assignee.FirstName} {assignee.LastName}.",
            UserId=current_user.UserId,
        ),
    )
    return issue


def update_status(
    db: Session, current_user: User, issue_id: int, payload: MaintenanceStatusUpdate
) -> MaintenanceIssue:
    issue = get_issue(db, current_user, issue_id)
    ensure_can_edit(current_user, issue)

    old_status = issue.Status
    new_status = _to_plain(payload.NewStatus)
    if new_status == old_status:
        raise ValidationError(f"Issue is already '{new_status}'.")

    issue.Status = new_status
    if new_status == "Completed" and issue.CompletedDate is None:
        issue.CompletedDate = date.today()
    issue = repo.save_issue(db, issue)

    repo.create_update(
        db,
        MaintenanceUpdate(
            MaintenanceIssueId=issue.MaintenanceIssueId,
            UpdateType="StatusChange",
            OldStatus=old_status,
            NewStatus=new_status,
            Comment=payload.Comment,
            UserId=current_user.UserId,
        ),
    )
    return issue


def add_note(
    db: Session, current_user: User, issue_id: int, payload: MaintenanceNoteCreate
) -> MaintenanceUpdate:
    issue = get_issue(db, current_user, issue_id)
    ensure_can_edit(current_user, issue)
    return repo.create_update(
        db,
        MaintenanceUpdate(
            MaintenanceIssueId=issue.MaintenanceIssueId,
            UpdateType="Comment",
            Comment=payload.Comment,
            UserId=current_user.UserId,
        ),
    )


def upload_photo(
    db: Session, current_user: User, issue_id: int, file: UploadFile, caption: str | None
) -> MediaFile:
    # Local import, not top-level: media_service's own entity-type dispatch needs to call BACK
    # into this module (ensure_can_edit, get_issue) for EntityType="MaintenanceIssue" - a
    # top-level import either direction would be circular. See media_service.py's
    # _view_maintenance_issue/_mutate_maintenance_issue for the matching local import there.
    # Reusing upload_media (rather than duplicating its content-type/size validation and storage
    # calls here) means this goes through the SAME permission check as any other MaintenanceIssue
    # media access - no separate code path to keep in sync.
    from app.services import media_service

    media_file = media_service.upload_media(
        db,
        current_user,
        entity_type="MaintenanceIssue",
        entity_id=issue_id,
        file=file,
        caption=caption,
    )
    repo.create_update(
        db,
        MaintenanceUpdate(
            MaintenanceIssueId=issue_id,
            UpdateType="PhotoUploaded",
            Comment=caption,
            UserId=current_user.UserId,
        ),
    )
    return media_file
