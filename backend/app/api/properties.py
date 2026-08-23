"""
Authorization per scope Prompt 7: "Managers/admins can manage properties. Inspectors can view
properties they have permission to inspect." The schema has no per-property assignment table
(not part of the original 25-table design - docs/DATABASE.md), so "permission to inspect" is
interpreted as company membership: any authenticated user in the property's company can view
(Administrator, Manager, Inspector, Maintenance, Viewer all plausibly need to see property
details to do their jobs), while only Administrator/Manager can create, edit, or deactivate.
Documented here as an explicit interpretive call, same as the enum-value decisions in
database/constraints/09_Constraints.sql.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.property import PropertyCreate, PropertyResponse, PropertyUpdate
from app.security import roles
from app.security.dependencies import get_current_user, require_roles
from app.services import property_service

router = APIRouter(prefix="/properties", tags=["properties"])

_manage_properties = require_roles(roles.ADMINISTRATOR, roles.MANAGER)


@router.get("", response_model=PaginatedResponse[PropertyResponse])
def list_properties(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    property_type: str | None = Query(default=None),
    property_status: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[PropertyResponse]:
    items, total = property_service.list_properties(
        db,
        current_user,
        page=page,
        page_size=page_size,
        search=search,
        property_type=property_type,
        property_status=property_status,
        include_inactive=include_inactive,
    )
    return PaginatedResponse(
        items=[PropertyResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PropertyResponse:
    property_ = property_service.get_property(db, current_user, property_id)
    return PropertyResponse.model_validate(property_)


@router.post("", response_model=PropertyResponse, status_code=201)
def create_property(
    payload: PropertyCreate,
    current_user: User = Depends(_manage_properties),
    db: Session = Depends(get_db),
) -> PropertyResponse:
    property_ = property_service.create_property(db, current_user, payload)
    return PropertyResponse.model_validate(property_)


@router.patch("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    current_user: User = Depends(_manage_properties),
    db: Session = Depends(get_db),
) -> PropertyResponse:
    property_ = property_service.update_property(db, current_user, property_id, payload)
    return PropertyResponse.model_validate(property_)


@router.post("/{property_id}/deactivate", response_model=PropertyResponse)
def deactivate_property(
    property_id: int,
    current_user: User = Depends(_manage_properties),
    db: Session = Depends(get_db),
) -> PropertyResponse:
    property_ = property_service.deactivate_property(db, current_user, property_id)
    return PropertyResponse.model_validate(property_)
