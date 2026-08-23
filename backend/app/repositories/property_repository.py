"""DB access only - no business rules (PROJECT_PLAN.md §5).

Every method here takes company_id as a required parameter and filters on it directly -
Properties has its own CompanyId column, so this is the straightforward case of the
company-isolation rule (docs/DATABASE.md §10.1), unlike the auth repository's deliberate
exceptions.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.property import Property


def list_properties(
    db: Session,
    company_id: int,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    property_type: str | None = None,
    property_status: str | None = None,
    include_inactive: bool = False,
) -> tuple[list[Property], int]:
    stmt = select(Property).where(Property.CompanyId == company_id)

    if not include_inactive:
        stmt = stmt.where(Property.IsActive == True)  # noqa: E712 - SQLAlchemy needs `== True`, not `is True`
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            (Property.PropertyName.ilike(like))
            | (Property.AddressLine1.ilike(like))
            | (Property.Postcode.ilike(like))
        )
    if property_type:
        stmt = stmt.where(Property.PropertyType == property_type)
    if property_status:
        stmt = stmt.where(Property.PropertyStatus == property_status)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    stmt = stmt.order_by(Property.PropertyName).offset((page - 1) * page_size).limit(page_size)
    items = list(db.execute(stmt).scalars().all())

    return items, total


def get_property_by_id(db: Session, company_id: int, property_id: int) -> Property | None:
    stmt = select(Property).where(Property.CompanyId == company_id, Property.PropertyId == property_id)
    return db.execute(stmt).scalar_one_or_none()


def create_property(db: Session, property_: Property) -> Property:
    db.add(property_)
    db.commit()
    db.refresh(property_)
    return property_


def save_property(db: Session, property_: Property) -> Property:
    """Used for both update and deactivate - the caller mutates the attributes it wants
    changed, this just persists them."""
    db.commit()
    db.refresh(property_)
    return property_
