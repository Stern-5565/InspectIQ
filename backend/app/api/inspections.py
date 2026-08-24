"""
"Start inspection" (POST) and "Resume inspection" (scope Prompt 8) are the same operation from
the API's point of view - there's no separate resume endpoint. Resuming an in-progress
inspection is just fetching it again by ID; its responses already persist from wherever the
inspector left off, since every answer/note/NA change is saved immediately (PATCH), not staged
in some draft state.

Role gating: starting/answering/submitting requires Administrator, Manager, or Inspector at the
route level (Maintenance/Viewer can't conduct inspections). A second, narrower check happens
inside the service layer for answering/submitting specifically: only the inspection's own
assigned inspector, or an Administrator/Manager, can modify it - see
app/services/inspection_service.py's ensure_can_edit for why that's stricter than the
route-level role check alone. Viewing (list/get) is open to any authenticated company user,
consistent with every other module so far.

Deliberately NOT built in this phase (scope Prompt 8 mentions them, but their own modules don't
exist yet): "Add photos/videos" (Phase 9), "Create maintenance issue from a response" (Phase
10), "Create risk assessment from a response" (Phase 13). InspectionResponseId already exists
as a stable FK target for all three once those modules arrive.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.inspection import (
    InspectionCreate,
    InspectionDetailResponse,
    InspectionResponseSchema,
    InspectionResponseUpdate,
    InspectionSummaryResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.security import roles
from app.security.dependencies import get_current_user, require_roles
from app.services import inspection_service

router = APIRouter(prefix="/inspections", tags=["inspections"])

_conduct_inspections = require_roles(roles.ADMINISTRATOR, roles.MANAGER, roles.INSPECTOR)


@router.post("", response_model=InspectionDetailResponse, status_code=201)
def start_inspection(
    payload: InspectionCreate,
    current_user: User = Depends(_conduct_inspections),
    db: Session = Depends(get_db),
) -> InspectionDetailResponse:
    inspection = inspection_service.start_inspection(db, current_user, payload)
    completion = inspection_service.calculate_completion_percentage(inspection.responses)
    return InspectionDetailResponse.from_inspection(inspection, completion)


@router.get("", response_model=PaginatedResponse[InspectionSummaryResponse])
def list_inspections(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    property_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    inspector_user_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[InspectionSummaryResponse]:
    items, total = inspection_service.list_inspections(
        db,
        current_user,
        page=page,
        page_size=page_size,
        property_id=property_id,
        status=status,
        inspector_user_id=inspector_user_id,
    )
    return PaginatedResponse(
        items=[InspectionSummaryResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{inspection_id}", response_model=InspectionDetailResponse)
def get_inspection(
    inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InspectionDetailResponse:
    inspection = inspection_service.get_inspection(db, current_user, inspection_id)
    completion = inspection_service.calculate_completion_percentage(inspection.responses)
    return InspectionDetailResponse.from_inspection(inspection, completion)


@router.patch("/{inspection_id}/responses/{response_id}", response_model=InspectionResponseSchema)
def update_response(
    inspection_id: int,
    response_id: int,
    payload: InspectionResponseUpdate,
    current_user: User = Depends(_conduct_inspections),
    db: Session = Depends(get_db),
) -> InspectionResponseSchema:
    response = inspection_service.update_response(db, current_user, inspection_id, response_id, payload)
    return InspectionResponseSchema.model_validate(response)


@router.post("/{inspection_id}/submit", response_model=InspectionDetailResponse)
def submit_inspection(
    inspection_id: int,
    current_user: User = Depends(_conduct_inspections),
    db: Session = Depends(get_db),
) -> InspectionDetailResponse:
    inspection_service.submit_inspection(db, current_user, inspection_id)
    # Re-fetched (rather than reusing submit_inspection's return value) to guarantee
    # .responses is loaded via the same joinedload path get_inspection always uses - a plain
    # db.refresh() after the status update doesn't reliably re-populate a relationship that
    # wasn't already loaded in this session.
    inspection = inspection_service.get_inspection(db, current_user, inspection_id)
    completion = inspection_service.calculate_completion_percentage(inspection.responses)
    return InspectionDetailResponse.from_inspection(inspection, completion)
