"""DB access only - no business rules.

VacantUnitInspections has no CompanyId of its own (same situation as CleaningInspections,
docs/DATABASE.md) - isolation joins through Inspections->Properties. list_for_inspection takes
no company_id, mirroring inspection_response_repository.py's convention: the service layer
always resolves and isolation-checks the parent Inspection first via
inspection_service.get_inspection before this function is ever called.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.property import Property
from app.models.unit import Unit
from app.models.vacant_unit_inspection import VacantUnitInspection


def create_vacant_unit_inspection(db: Session, record: VacantUnitInspection) -> VacantUnitInspection:
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_vacant_unit_inspection_by_id(
    db: Session, company_id: int, vacant_unit_inspection_id: int
) -> VacantUnitInspection | None:
    stmt = (
        select(VacantUnitInspection)
        .join(Inspection, Inspection.InspectionId == VacantUnitInspection.InspectionId)
        .join(Property, Property.PropertyId == Inspection.PropertyId)
        .where(
            Property.CompanyId == company_id,
            VacantUnitInspection.VacantUnitInspectionId == vacant_unit_inspection_id,
        )
    )
    return db.execute(stmt).scalar_one_or_none()


def list_for_inspection(db: Session, inspection_id: int) -> list[VacantUnitInspection]:
    stmt = (
        select(VacantUnitInspection)
        .where(VacantUnitInspection.InspectionId == inspection_id)
        .order_by(VacantUnitInspection.VacantUnitInspectionId)
    )
    return list(db.execute(stmt).scalars().all())


def list_vacant_unit_inspections_for_company(
    db: Session,
    company_id: int,
    *,
    page: int,
    page_size: int,
    property_id: int | None = None,
) -> tuple[list, int]:
    """The standalone Vacant Units module's own query - added alongside the module's frontend,
    same reasoning as cleaning_repository.list_cleaning_inspections_for_company: every prior
    VacantUnitInspection query was scoped to one already-authorized Inspection
    (list_for_inspection above); nothing before this queried across a whole company. Joins Unit
    too (for UnitNumber) so the summary response doesn't need a second round-trip per row."""
    stmt = (
        select(VacantUnitInspection, Inspection.PropertyId, Unit.UnitNumber)
        .join(Inspection, Inspection.InspectionId == VacantUnitInspection.InspectionId)
        .join(Unit, Unit.UnitId == VacantUnitInspection.UnitId)
        .join(Property, Property.PropertyId == Inspection.PropertyId)
        .where(Property.CompanyId == company_id)
    )
    if property_id is not None:
        stmt = stmt.where(Inspection.PropertyId == property_id)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    stmt = (
        stmt.order_by(VacantUnitInspection.VacantUnitInspectionId.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list(db.execute(stmt).all())
    return rows, total


def save_vacant_unit_inspection(db: Session, record: VacantUnitInspection) -> VacantUnitInspection:
    db.commit()
    db.refresh(record)
    return record
