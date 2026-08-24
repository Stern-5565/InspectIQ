"""
Single authorization tier, matching app/services/vacant_unit_service.py's module docstring:
view (list) is open to any authenticated company user; create/update are gated at the ROUTE
level to Administrator/Manager/Inspector (Maintenance/Viewer can't conduct inspections, the same
`_conduct_inspections` tier Phase 8/11 already use), narrowed further at the SERVICE level to
the inspection's own assigned inspector or Admin/Manager.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.vacant_unit_inspection import (
    VacantUnitInspectionCreate,
    VacantUnitInspectionResponse,
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
