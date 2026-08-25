"""
Two sub-resources, two authorization shapes - see app/services/cleaning_service.py's module
docstring for the full reasoning. CleaningAreas mirror Properties/Units exactly (view = any
company member, mutate = Administrator/Manager only, gated by `require_roles` at the route
level). CleaningInspections mirror the Inspection engine (Phase 8): view = any company member,
mutate open to Administrator/Manager/Inspector at the route level (Maintenance/Viewer can't
conduct inspections, same tier as starting/answering one), narrowed further at the service
level to the inspection's own assigned inspector or Admin/Manager
(`inspection_service.ensure_can_edit`).

`GET /cleaning-inspections` and `GET /cleaning-inspections/{id}` were added for the standalone
Cleaning module's frontend, not part of Phase 11 - every CleaningInspection query before this
was scoped to one already-authorized Inspection, with no way to browse grading history across
the company the way Maintenance/Risk already could. View-level, no role restriction, same as
every other list/detail pair in this project.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.cleaning import (
    CleaningAreaCreate,
    CleaningAreaResponse,
    CleaningAreaUpdate,
    CleaningInspectionCreate,
    CleaningInspectionResponse,
    CleaningInspectionSummaryResponse,
    CleaningInspectionUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.security import roles
from app.security.dependencies import get_current_user, require_roles
from app.services import cleaning_service

router = APIRouter(tags=["cleaning"])

_manage_areas = require_roles(roles.ADMINISTRATOR, roles.MANAGER)
_conduct_inspections = require_roles(roles.ADMINISTRATOR, roles.MANAGER, roles.INSPECTOR)


@router.post(
    "/properties/{property_id}/cleaning-areas", response_model=CleaningAreaResponse, status_code=201
)
def create_area(
    property_id: int,
    payload: CleaningAreaCreate,
    current_user: User = Depends(_manage_areas),
    db: Session = Depends(get_db),
) -> CleaningAreaResponse:
    area = cleaning_service.create_area(db, current_user, property_id, payload)
    return CleaningAreaResponse.model_validate(area)


@router.get("/properties/{property_id}/cleaning-areas", response_model=list[CleaningAreaResponse])
def list_areas(
    property_id: int,
    include_inactive: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CleaningAreaResponse]:
    areas = cleaning_service.list_areas(db, current_user, property_id, include_inactive=include_inactive)
    return [CleaningAreaResponse.model_validate(a) for a in areas]


@router.patch("/cleaning-areas/{area_id}", response_model=CleaningAreaResponse)
def update_area(
    area_id: int,
    payload: CleaningAreaUpdate,
    current_user: User = Depends(_manage_areas),
    db: Session = Depends(get_db),
) -> CleaningAreaResponse:
    area = cleaning_service.update_area(db, current_user, area_id, payload)
    return CleaningAreaResponse.model_validate(area)


@router.post(
    "/inspections/{inspection_id}/cleaning", response_model=CleaningInspectionResponse, status_code=201
)
def create_cleaning_inspection(
    inspection_id: int,
    payload: CleaningInspectionCreate,
    current_user: User = Depends(_conduct_inspections),
    db: Session = Depends(get_db),
) -> CleaningInspectionResponse:
    cleaning_inspection = cleaning_service.create_cleaning_inspection(db, current_user, inspection_id, payload)
    return CleaningInspectionResponse.model_validate(cleaning_inspection)


@router.get("/inspections/{inspection_id}/cleaning", response_model=list[CleaningInspectionResponse])
def list_cleaning_inspections(
    inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CleaningInspectionResponse]:
    items = cleaning_service.list_cleaning_inspections(db, current_user, inspection_id)
    return [CleaningInspectionResponse.model_validate(i) for i in items]


@router.patch("/cleaning-inspections/{cleaning_inspection_id}", response_model=CleaningInspectionResponse)
def update_cleaning_inspection(
    cleaning_inspection_id: int,
    payload: CleaningInspectionUpdate,
    current_user: User = Depends(_conduct_inspections),
    db: Session = Depends(get_db),
) -> CleaningInspectionResponse:
    cleaning_inspection = cleaning_service.update_cleaning_inspection(
        db, current_user, cleaning_inspection_id, payload
    )
    return CleaningInspectionResponse.model_validate(cleaning_inspection)


@router.get("/cleaning-inspections", response_model=PaginatedResponse[CleaningInspectionSummaryResponse])
def list_all_cleaning_inspections(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    property_id: int | None = Query(default=None),
    grade: str | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[CleaningInspectionSummaryResponse]:
    rows, total = cleaning_service.list_cleaning_inspections_for_company(
        db, current_user, page=page, page_size=page_size, property_id=property_id, grade=grade, status=status
    )
    return PaginatedResponse(
        items=[CleaningInspectionSummaryResponse.from_row(ci, prop_id, area_name) for ci, prop_id, area_name in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/cleaning-inspections/{cleaning_inspection_id}", response_model=CleaningInspectionSummaryResponse)
def get_cleaning_inspection_detail(
    cleaning_inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CleaningInspectionSummaryResponse:
    cleaning_inspection, property_id, area_name = cleaning_service.get_cleaning_inspection_detail(
        db, current_user, cleaning_inspection_id
    )
    return CleaningInspectionSummaryResponse.from_row(cleaning_inspection, property_id, area_name)
