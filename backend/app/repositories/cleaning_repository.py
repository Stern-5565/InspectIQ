"""DB access only - no business rules.

Neither CleaningAreas nor CleaningInspections carries its own CompanyId (docs/DATABASE.md's
table sketch - unlike MediaFiles/MaintenanceIssues, which denormalize it). CleaningArea
isolation joins through Properties; CleaningInspection isolation joins through
Inspections->Properties. list_cleaning_inspections_for_inspection takes no company_id, mirroring
inspection_response_repository.py's convention exactly: the service layer always resolves and
isolation-checks the parent Inspection first via inspection_service.get_inspection before this
function is ever called.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cleaning_area import CleaningArea
from app.models.cleaning_inspection import CleaningInspection
from app.models.inspection import Inspection
from app.models.property import Property


def create_area(db: Session, area: CleaningArea) -> CleaningArea:
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def create_areas_bulk(db: Session, areas: list[CleaningArea]) -> None:
    db.add_all(areas)
    db.commit()


def get_area_by_id(db: Session, company_id: int, area_id: int) -> CleaningArea | None:
    stmt = (
        select(CleaningArea)
        .join(Property, Property.PropertyId == CleaningArea.PropertyId)
        .where(Property.CompanyId == company_id, CleaningArea.CleaningAreaId == area_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_areas_for_property(
    db: Session, company_id: int, property_id: int, *, include_inactive: bool = False
) -> list[CleaningArea]:
    stmt = (
        select(CleaningArea)
        .join(Property, Property.PropertyId == CleaningArea.PropertyId)
        .where(Property.CompanyId == company_id, CleaningArea.PropertyId == property_id)
    )
    if not include_inactive:
        stmt = stmt.where(CleaningArea.IsActive == True)  # noqa: E712
    stmt = stmt.order_by(CleaningArea.AreaName)
    return list(db.execute(stmt).scalars().all())


def save_area(db: Session, area: CleaningArea) -> CleaningArea:
    db.commit()
    db.refresh(area)
    return area


def create_cleaning_inspection(db: Session, cleaning_inspection: CleaningInspection) -> CleaningInspection:
    db.add(cleaning_inspection)
    db.commit()
    db.refresh(cleaning_inspection)
    return cleaning_inspection


def get_cleaning_inspection_by_id(
    db: Session, company_id: int, cleaning_inspection_id: int
) -> CleaningInspection | None:
    stmt = (
        select(CleaningInspection)
        .join(Inspection, Inspection.InspectionId == CleaningInspection.InspectionId)
        .join(Property, Property.PropertyId == Inspection.PropertyId)
        .where(
            Property.CompanyId == company_id,
            CleaningInspection.CleaningInspectionId == cleaning_inspection_id,
        )
    )
    return db.execute(stmt).scalar_one_or_none()


def list_cleaning_inspections_for_inspection(db: Session, inspection_id: int) -> list[CleaningInspection]:
    stmt = (
        select(CleaningInspection)
        .where(CleaningInspection.InspectionId == inspection_id)
        .order_by(CleaningInspection.CleaningInspectionId)
    )
    return list(db.execute(stmt).scalars().all())


def save_cleaning_inspection(db: Session, cleaning_inspection: CleaningInspection) -> CleaningInspection:
    db.commit()
    db.refresh(cleaning_inspection)
    return cleaning_inspection
