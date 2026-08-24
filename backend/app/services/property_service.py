from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.property import Property
from app.models.user import User
from app.repositories import property_repository as repo
from app.schemas.property import PropertyCreate, PropertyUpdate


def _to_plain(value: Any) -> Any:
    """Pydantic keeps enum fields as enum members on model_dump() (mode="python", the
    default) - the ORM's String columns need their plain .value. Deliberately not using
    model_dump(mode="json") for this: that would also turn date fields into ISO strings,
    which the SQLAlchemy Date column type doesn't expect from the ORM layer."""
    return value.value if isinstance(value, Enum) else value


def list_properties(
    db: Session,
    current_user: User,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    property_type: str | None = None,
    property_status: str | None = None,
    include_inactive: bool = False,
) -> tuple[list[Property], int]:
    return repo.list_properties(
        db,
        current_user.CompanyId,
        page=page,
        page_size=page_size,
        search=search,
        property_type=property_type,
        property_status=property_status,
        include_inactive=include_inactive,
    )


def get_property(db: Session, current_user: User, property_id: int) -> Property:
    property_ = repo.get_property_by_id(db, current_user.CompanyId, property_id)
    if property_ is None:
        # 404, not 403 - a property belonging to another company must be indistinguishable
        # from a property that doesn't exist at all (docs/DATABASE.md §10.1). A 403 would
        # confirm to an attacker that *something* exists at that ID, just not for them.
        raise NotFoundError("Property not found.")
    return property_


def create_property(db: Session, current_user: User, payload: PropertyCreate) -> Property:
    data = {field: _to_plain(value) for field, value in payload.model_dump().items()}
    property_ = Property(CompanyId=current_user.CompanyId, CreatedBy=current_user.UserId, **data)
    property_ = repo.create_property(db, property_)

    # Local import, not top-level: cleaning_service imports property_service (for its own
    # CleaningArea authorization checks), so a top-level import here would be circular - the
    # same pattern used for media_service<->maintenance_service in Phase 10. Auto-seeding a
    # default area set closes the onboarding gap docs/DATABASE.md §10 flagged: "a new property
    # has zero cleaning areas until someone configures them." Not a separately authorized
    # action - this property was just created by an already-authorized caller.
    from app.services import cleaning_service

    cleaning_service.seed_default_areas_for_property(db, property_)

    return property_


def update_property(
    db: Session, current_user: User, property_id: int, payload: PropertyUpdate
) -> Property:
    property_ = get_property(db, current_user, property_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(property_, field, _to_plain(value))
    return repo.save_property(db, property_)


def deactivate_property(db: Session, current_user: User, property_id: int) -> Property:
    property_ = get_property(db, current_user, property_id)
    property_.IsActive = False
    return repo.save_property(db, property_)
