"""
Single authorization tier, matching app/services/vacant_unit_service.py's module docstring:
view (list) is open to any authenticated company user; create/update are gated at the ROUTE
level to Administrator/Manager/Inspector (Maintenance/Viewer can't conduct inspections, the same
`_conduct_inspections` tier Phase 8/11 already use), narrowed further at the SERVICE level to
the inspection's own assigned inspector or Admin/Manager.

`GET /vacant-unit-inspections` and `GET /vacant-unit-inspections/{id}` were added for the
standalone Vacant Units module's own list/detail pages - see
app/repositories/vacant_unit_inspection_repository.py's list_vacant_unit_inspections_for_company
docstring for why nothing before this queried across a whole company (mirrors
app/api/cleaning.py's exact addition for the same reason).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.vacant_unit_inspection import (
    VacantUnitInspectionCreate,
    VacantUnitInspectionResponse,
    VacantUnitInspectionSummaryResponse,
    VacantUnitInspectionUpdate,
)
from app.security import roles
from app.security.dependencies import get_current_user, require_roles
from app.services import vacant_unit_service

router = APIRouter(tags=["vacant-unit-inspections"])

_conduct_inspections = require_roles(roles.ADMINISTRATOR, roles.MANAGER, roles.INSPECTOR)


@router.post(
    "/inspections/{inspection_id}/vacant-unit-inspections",
    response_model=VacantUnitInspectionResponse,
    status_code=201,
)
def create_vacant_unit_inspection(
    inspection_id: int,
    payload: VacantUnitInspectionCreate,
    current_user: User = Depends(_conduct_inspections),
    db: Session = Depends(get_db),
) -> VacantUnitInspectionResponse:
    record = vacant_unit_service.create_vacant_unit_inspection(db, current_user, inspection_id, payload)
    return VacantUnitInspectionResponse.model_validate(record)


@router.get(
    "/inspections/{inspection_id}/vacant-unit-inspections",
    response_model=list[VacantUnitInspectionResponse],
)
def list_vacant_unit_inspections(
    inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VacantUnitInspectionResponse]:
    items = vacant_unit_service.list_vacant_unit_inspections(db, current_user, inspection_id)
    return [VacantUnitInspectionResponse.model_validate(i) for i in items]


@router.patch(
    "/vacant-unit-inspections/{vacant_unit_inspection_id}", response_model=VacantUnitInspectionResponse
)
def update_vacant_unit_inspection(
    vacant_unit_inspection_id: int,
    payload: VacantUnitInspectionUpdate,
    current_user: User = Depends(_conduct_inspections),
    db: Session = Depends(get_db),
) -> VacantUnitInspectionResponse:
    record = vacant_unit_service.update_vacant_unit_inspection(
        db, current_user, vacant_unit_inspection_id, payload
    )
    return VacantUnitInspectionResponse.model_validate(record)


@router.get(
    "/vacant-unit-inspections", response_model=PaginatedResponse[VacantUnitInspectionSummaryResponse]
)
def list_all_vacant_unit_inspections(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    property_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[VacantUnitInspectionSummaryResponse]:
    rows, total = vacant_unit_service.list_vacant_unit_inspections_for_company(
        db, current_user, page=page, page_size=page_size, property_id=property_id
    )
    return PaginatedResponse(
        items=[VacantUnitInspectionSummaryResponse.from_row(r, prop_id, unit_number) for r, prop_id, unit_number in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/vacant-unit-inspections/{vacant_unit_inspection_id}",
    response_model=VacantUnitInspectionSummaryResponse,
)
def get_vacant_unit_inspection_detail(
    vacant_unit_inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VacantUnitInspectionSummaryResponse:
    record, property_id, unit_number = vacant_unit_service.get_vacant_unit_inspection_detail(
        db, current_user, vacant_unit_inspection_id
    )
    return VacantUnitInspectionSummaryResponse.from_row(record, property_id, unit_number)
