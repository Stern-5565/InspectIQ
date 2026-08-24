"""DB access only - no business rules.

VacantUnitInspections has no CompanyId of its own (same situation as CleaningInspections,
docs/DATABASE.md) - isolation joins through Inspections->Properties. list_for_inspection takes
no company_id, mirroring inspection_response_repository.py's convention: the service layer
always resolves and isolation-checks the parent Inspection first via
inspection_service.get_inspection before this function is ever called.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.property import Property
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


def save_vacant_unit_inspection(db: Session, record: VacantUnitInspection) -> VacantUnitInspection:
    db.commit()
    db.refresh(record)
    return record
