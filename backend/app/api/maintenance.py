"""
Route-level role gating is deliberately uneven across this router - see
app/services/maintenance_service.py's module docstring for the full three-tier authorization
story. Summary: create requires Administrator/Manager/Inspector (same tier as starting an
inspection - Inspector "raises maintenance" per scope's own role description); general
edit/assign require Administrator/Manager only; status/notes/photos are open to any
authenticated user at the ROUTE level because the real gate - the issue's own assigned user, or
Administrator/Manager - can only be evaluated once the specific issue is loaded, which is what
`maintenance_service.ensure_can_edit` does. Viewing (list/get/timeline) has no role restriction,
consistent with every other module.
"""
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.maintenance import (
    MaintenanceAssignmentUpdate,
    MaintenanceIssueCreate,
    MaintenanceIssueDetailResponse,
    MaintenanceIssueSummaryResponse,
    MaintenanceIssueUpdate,
    MaintenanceNoteCreate,
    MaintenanceStatusUpdate,
    MaintenanceUpdateResponse,
)
from app.schemas.media_file import MediaFileResponse
from app.schemas.pagination import PaginatedResponse
from app.security import roles
from app.security.dependencies import get_current_user, require_roles
from app.services import maintenance_service

router = APIRouter(prefix="/maintenance-issues", tags=["maintenance"])

_raise_issues = require_roles(roles.ADMINISTRATOR, roles.MANAGER, roles.INSPECTOR)
_manage_issues = require_roles(roles.ADMINISTRATOR, roles.MANAGER)


def _detail(db: Session, current_user: User, issue) -> MaintenanceIssueDetailResponse:
    updates = maintenance_service.list_timeline(db, current_user, issue.MaintenanceIssueId)
    return MaintenanceIssueDetailResponse.from_issue(issue, updates)


@router.post("", response_model=MaintenanceIssueDetailResponse, status_code=201)
def create_issue(
    payload: MaintenanceIssueCreate,
    current_user: User = Depends(_raise_issues),
    db: Session = Depends(get_db),
) -> MaintenanceIssueDetailResponse:
    issue = maintenance_service.create_issue(db, current_user, payload)
    return _detail(db, current_user, issue)


@router.get("", response_model=PaginatedResponse[MaintenanceIssueSummaryResponse])
def list_issues(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    property_id: int | None = Query(default=None),
    assigned_user_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[MaintenanceIssueSummaryResponse]:
    items, total = maintenance_service.list_issues(
        db,
        current_user,
        page=page,
        page_size=page_size,
        status=status,
        category=category,
        priority=priority,
        property_id=property_id,
        assigned_user_id=assigned_user_id,
    )
    return PaginatedResponse(
        items=[MaintenanceIssueSummaryResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{issue_id}", response_model=MaintenanceIssueDetailResponse)
def get_issue(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceIssueDetailResponse:
    issue = maintenance_service.get_issue(db, current_user, issue_id)
    return _detail(db, current_user, issue)


@router.get("/{issue_id}/timeline", response_model=list[MaintenanceUpdateResponse])
def get_timeline(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaintenanceUpdateResponse]:
    updates = maintenance_service.list_timeline(db, current_user, issue_id)
    return [MaintenanceUpdateResponse.model_validate(u) for u in updates]


@router.patch("/{issue_id}", response_model=MaintenanceIssueDetailResponse)
def update_issue(
    issue_id: int,
    payload: MaintenanceIssueUpdate,
    current_user: User = Depends(_manage_issues),
    db: Session = Depends(get_db),
) -> MaintenanceIssueDetailResponse:
    issue = maintenance_service.update_issue(db, current_user, issue_id, payload)
    return _detail(db, current_user, issue)


@router.patch("/{issue_id}/assign", response_model=MaintenanceIssueDetailResponse)
def assign_issue(
    issue_id: int,
    payload: MaintenanceAssignmentUpdate,
    current_user: User = Depends(_manage_issues),
    db: Session = Depends(get_db),
) -> MaintenanceIssueDetailResponse:
    issue = maintenance_service.assign_issue(db, current_user, issue_id, payload)
    return _detail(db, current_user, issue)


@router.patch("/{issue_id}/status", response_model=MaintenanceIssueDetailResponse)
def update_status(
    issue_id: int,
    payload: MaintenanceStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceIssueDetailResponse:
    issue = maintenance_service.update_status(db, current_user, issue_id, payload)
    return _detail(db, current_user, issue)


@router.post("/{issue_id}/notes", response_model=MaintenanceUpdateResponse, status_code=201)
def add_note(
    issue_id: int,
    payload: MaintenanceNoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceUpdateResponse:
    update = maintenance_service.add_note(db, current_user, issue_id, payload)
    return MaintenanceUpdateResponse.model_validate(update)


@router.post("/{issue_id}/photos", response_model=MediaFileResponse, status_code=201)
def upload_photo(
    issue_id: int,
    caption: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MediaFileResponse:
    media_file = maintenance_service.upload_photo(db, current_user, issue_id, file, caption)
    return MediaFileResponse.model_validate(media_file)
