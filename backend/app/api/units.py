"""
Same authorization interpretation as app/api/properties.py: view = any authenticated company
user, mutate = Administrator/Manager only. Occupancy-status changes are kept in that same
Administrator/Manager bracket for this phase, even though realistically an Inspector doing a
walkthrough is often the one who discovers a unit is now vacant - that flow belongs to the
Inspection engine (Phase 8), which will call into unit occupancy updates through its own
service with its own permission story, not through this standalone API. Revisit if Phase 8
needs a different answer here.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.unit import UnitCreate, UnitOccupancyUpdate, UnitResponse, UnitUpdate
from app.security import roles
from app.security.dependencies import get_current_user, require_roles
from app.services import unit_service

router = APIRouter(tags=["units"])

_manage_units = require_roles(roles.ADMINISTRATOR, roles.MANAGER)


@router.get("/properties/{property_id}/units", response_model=PaginatedResponse[UnitResponse])
def list_units(
    property_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    occupancy_status: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[UnitResponse]:
    items, total = unit_service.list_units(
        db,
        current_user,
        property_id,
        page=page,
        page_size=page_size,
        occupancy_status=occupancy_status,
        include_inactive=include_inactive,
    )
    return PaginatedResponse(
        items=[UnitResponse.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/properties/{property_id}/units", response_model=UnitResponse, status_code=201)
def create_unit(
    property_id: int,
    payload: UnitCreate,
    current_user: User = Depends(_manage_units),
    db: Session = Depends(get_db),
) -> UnitResponse:
    unit = unit_service.create_unit(db, current_user, property_id, payload)
    return UnitResponse.model_validate(unit)


@router.get("/units/{unit_id}", response_model=UnitResponse)
def get_unit(
    unit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnitResponse:
    unit = unit_service.get_unit(db, current_user, unit_id)
    return UnitResponse.model_validate(unit)


@router.patch("/units/{unit_id}", response_model=UnitResponse)
def update_unit(
    unit_id: int,
    payload: UnitUpdate,
    current_user: User = Depends(_manage_units),
    db: Session = Depends(get_db),
) -> UnitResponse:
    unit = unit_service.update_unit(db, current_user, unit_id, payload)
    return UnitResponse.model_validate(unit)


@router.patch("/units/{unit_id}/occupancy", response_model=UnitResponse)
def update_unit_occupancy(
    unit_id: int,
    payload: UnitOccupancyUpdate,
    current_user: User = Depends(_manage_units),
    db: Session = Depends(get_db),
) -> UnitResponse:
    unit = unit_service.update_unit_occupancy(db, current_user, unit_id, payload)
    return UnitResponse.model_validate(unit)
