"""DB access only - no business rules.

MeterReadings has no CompanyId of its own, but PropertyId is NOT NULL and directly present
(unlike Units/Inspections, which need a join to reach it or don't have it at all) - isolation is
a single join to Properties, the simplest case of any module so far.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
) -> tuple[list[MeterReading], int]:
    stmt = (
        select(MeterReading)
        .join(Property, Property.PropertyId == MeterReading.PropertyId)
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
    items = list(db.execute(stmt).scalars().all())

    return items, total


def save_meter_reading(db: Session, reading: MeterReading) -> MeterReading:
    db.commit()
    db.refresh(reading)
    return reading
