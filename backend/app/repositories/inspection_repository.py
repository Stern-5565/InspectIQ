"""DB access only - no business rules.

Inspections has no CompanyId column of its own (same situation as Units, docs/DATABASE.md
§9.5) - every isolation-sensitive query joins through Properties and filters on
Properties.CompanyId.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.inspection import Inspection
from app.models.property import Property


def create_inspection(db: Session, inspection: Inspection) -> Inspection:
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return inspection


def list_inspections(
    db: Session,
    company_id: int,
    *,
    page: int,
    page_size: int,
    property_id: int | None = None,
    status: str | None = None,
    inspector_user_id: int | None = None,
) -> tuple[list[Inspection], int]:
    stmt = (
        select(Inspection)
        .join(Property, Property.PropertyId == Inspection.PropertyId)
        .where(Property.CompanyId == company_id)
    )

    if property_id is not None:
        stmt = stmt.where(Inspection.PropertyId == property_id)
    if status is not None:
        stmt = stmt.where(Inspection.Status == status)
    if inspector_user_id is not None:
        stmt = stmt.where(Inspection.InspectorUserId == inspector_user_id)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    stmt = stmt.order_by(Inspection.InspectionDate.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.execute(stmt).scalars().all())

    return items, total


def get_inspection_by_id(db: Session, company_id: int, inspection_id: int) -> Inspection | None:
    stmt = (
        select(Inspection)
        .join(Property, Property.PropertyId == Inspection.PropertyId)
        .where(Property.CompanyId == company_id, Inspection.InspectionId == inspection_id)
        .options(joinedload(Inspection.responses))
    )
    return db.execute(stmt).unique().scalar_one_or_none()


def save_inspection(db: Session, inspection: Inspection) -> Inspection:
    db.commit()
    db.refresh(inspection)
    return inspection
