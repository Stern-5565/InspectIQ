from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.unit import Unit
from app.models.user import User
from app.repositories import unit_repository as repo
from app.services.property_service import get_property
from app.schemas.unit import UnitCreate, UnitOccupancyUpdate, UnitUpdate


def _to_plain(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def list_units(
    db: Session,
    current_user: User,
    property_id: int,
    *,
    page: int,
    page_size: int,
    occupancy_status: str | None = None,
    include_inactive: bool = False,
) -> tuple[list[Unit], int]:
    # Confirms the property exists and belongs to the caller's company first (404 if not) -
    # otherwise an empty unit list for a wrong-company property_id would look identical to an
    # empty list for a real property with no units yet, which is a confusing API, not a
    # security issue by itself but still the wrong shape of "not found."
    get_property(db, current_user, property_id)
    return repo.list_units_by_property(
        db,
        current_user.CompanyId,
        property_id,
        page=page,
        page_size=page_size,
        occupancy_status=occupancy_status,
        include_inactive=include_inactive,
    )


def get_unit(db: Session, current_user: User, unit_id: int) -> Unit:
    unit = repo.get_unit_by_id(db, current_user.CompanyId, unit_id)
    if unit is None:
        raise NotFoundError("Unit not found.")
    return unit


def create_unit(db: Session, current_user: User, property_id: int, payload: UnitCreate) -> Unit:
    get_property(db, current_user, property_id)  # 404s if property_id isn't in this company
    data = {field: _to_plain(value) for field, value in payload.model_dump().items()}
    unit = Unit(PropertyId=property_id, **data)
    return repo.create_unit(db, unit)


def update_unit(db: Session, current_user: User, unit_id: int, payload: UnitUpdate) -> Unit:
    unit = get_unit(db, current_user, unit_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(unit, field, _to_plain(value))
    return repo.save_unit(db, unit)


def update_unit_occupancy(
    db: Session, current_user: User, unit_id: int, payload: UnitOccupancyUpdate
) -> Unit:
    unit = get_unit(db, current_user, unit_id)
    unit.OccupancyStatus = _to_plain(payload.OccupancyStatus)
    return repo.save_unit(db, unit)
