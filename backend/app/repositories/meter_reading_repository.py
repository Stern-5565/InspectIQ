"""DB access only - no business rules.

MeterReadings has no CompanyId of its own, but PropertyId is NOT NULL and directly present
(unlike Units/Inspections, which need a join to reach it or don't have it at all) - isolation is
a single join to Properties, the simplest case of any module so far.

Unlike Cleaning/VacantUnits, this module's list/detail queries were ALREADY company-wide since
Phase 14 (MeterReadings was never nested under one Inspection the way CleaningInspections/
VacantUnitInspections were) - so the standalone Phase 16 module needed no new ROUTES, just
PropertyName/InspectionId joined onto the existing list/detail queries for display. InspectionId
is reached via an OUTER join through InspectionResponses (MeterReading.InspectionResponseId is
nullable - a standalone reading has no Inspection at all, so this is None for those rows, not a
failed join)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.inspection_response import InspectionResponse
from app.models.meter_reading import MeterReading
from app.models.property import Property


def create_meter_reading(db: Session, reading: MeterReading) -> MeterReading:
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


def get_meter_reading_by_id(db: Session, company_id: int, meter_reading_id: int) -> MeterReading | None:
    stmt = (
        select(MeterReading)
        .join(Property, Property.PropertyId == MeterReading.PropertyId)
        .where(Property.CompanyId == company_id, MeterReading.MeterReadingId == meter_reading_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_meter_readings(
    db: Session,
    company_id: int,
    *,
    page: int,
    page_size: int,
    property_id: int | None = None,
    meter_type: str | None = None,
    inspection_response_id: int | None = None,
) -> tuple[list, int]:
    """Returns (MeterReading, PropertyName, InspectionId) rows, not bare MeterReading - the
    standalone module's list page needs both for display, and this is the ONLY caller of this
    query (unlike get_meter_reading_by_id below, which several other services also call for a
    bare ORM object), so enriching it in place is safe rather than adding a parallel function."""
    stmt = (
        select(MeterReading, Property.PropertyName, InspectionResponse.InspectionId)
        .join(Property, Property.PropertyId == MeterReading.PropertyId)
        .outerjoin(
            InspectionResponse,
            InspectionResponse.InspectionResponseId == MeterReading.InspectionResponseId,
        )
        .where(Property.CompanyId == company_id)
    )
    if property_id is not None:
        stmt = stmt.where(MeterReading.PropertyId == property_id)
    if meter_type is not None:
        stmt = stmt.where(MeterReading.MeterType == meter_type)
    if inspection_response_id is not None:
        stmt = stmt.where(MeterReading.InspectionResponseId == inspection_response_id)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    stmt = (
        stmt.order_by(MeterReading.ReadingDateTime.desc(), MeterReading.MeterReadingId.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list(db.execute(stmt).all())

    return rows, total


def get_meter_reading_with_property_name(db: Session, company_id: int, meter_reading_id: int):
    """The standalone module's own single-detail lookup - kept SEPARATE from
    get_meter_reading_by_id above (which stays a bare MeterReading | None, since
    meter_reading_service.get_meter_reading wraps it and several other services depend on that
    exact shape: media_service's authorization dispatch, update_meter_reading's mutation).
    Returns a (MeterReading, PropertyName, InspectionId) row, or None."""
    stmt = (
        select(MeterReading, Property.PropertyName, InspectionResponse.InspectionId)
        .join(Property, Property.PropertyId == MeterReading.PropertyId)
        .outerjoin(
            InspectionResponse,
            InspectionResponse.InspectionResponseId == MeterReading.InspectionResponseId,
        )
        .where(Property.CompanyId == company_id, MeterReading.MeterReadingId == meter_reading_id)
    )
    return db.execute(stmt).first()


def save_meter_reading(db: Session, reading: MeterReading) -> MeterReading:
    db.commit()
    db.refresh(reading)
    return reading
