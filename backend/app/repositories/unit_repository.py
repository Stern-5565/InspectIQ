"""DB access only - no business rules.

Units has no CompanyId column of its own (docs/DATABASE.md §2/§9.5 - only the second/third-tier
tables that needed direct isolation queries got a denormalized CompanyId; Units is reached via
its Property, which is a cheap single join, so it didn't need one). Every method here joins to
Properties and filters on Properties.CompanyId - never trust a UnitId alone to imply
company-scoping, and never accept company_id from anywhere but the authenticated user.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.unit import Unit


def list_units_by_property(
    db: Session,
    company_id: int,
    property_id: int,
    *,
    page: int,
    page_size: int,
    occupancy_status: str | None = None,
    include_inactive: bool = False,
) -> tuple[list[Unit], int]:
    stmt = (
        select(Unit)
        .join(Property, Property.PropertyId == Unit.PropertyId)
        .where(Property.CompanyId == company_id, Unit.PropertyId == property_id)
    )

    if not include_inactive:
        stmt = stmt.where(Unit.IsActive == True)  # noqa: E712
    if occupancy_status:
        stmt = stmt.where(Unit.OccupancyStatus == occupancy_status)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    stmt = stmt.order_by(Unit.UnitNumber).offset((page - 1) * page_size).limit(page_size)
    items = list(db.execute(stmt).scalars().all())

    return items, total


def get_unit_by_id(db: Session, company_id: int, unit_id: int) -> Unit | None:
    stmt = (
        select(Unit)
        .join(Property, Property.PropertyId == Unit.PropertyId)
        .where(Property.CompanyId == company_id, Unit.UnitId == unit_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def create_unit(db: Session, unit: Unit) -> Unit:
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def save_unit(db: Session, unit: Unit) -> Unit:
    db.commit()
    db.refresh(unit)
    return unit
