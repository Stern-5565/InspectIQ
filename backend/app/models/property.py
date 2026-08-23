from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.unit import Unit
    from app.models.user import User


class Property(Base):
    __tablename__ = "Properties"

    PropertyId: Mapped[int] = mapped_column(Integer, primary_key=True)
    CompanyId: Mapped[int] = mapped_column(Integer, ForeignKey("Companies.CompanyId"), nullable=False)
    PropertyName: Mapped[str] = mapped_column(String(200), nullable=False)
    AddressLine1: Mapped[str] = mapped_column(String(200), nullable=False)
    AddressLine2: Mapped[str | None] = mapped_column(String(200))
    City: Mapped[str | None] = mapped_column(String(100))
    Postcode: Mapped[str] = mapped_column(String(20), nullable=False)
    PropertyType: Mapped[str] = mapped_column(String(50), nullable=False)
    PropertyStatus: Mapped[str] = mapped_column(String(50), nullable=False)
    NumberOfUnits: Mapped[int | None] = mapped_column(Integer)
    MainContactName: Mapped[str | None] = mapped_column(String(200))
    MainContactPhone: Mapped[str | None] = mapped_column(String(30))
    MainContactEmail: Mapped[str | None] = mapped_column(String(200))
    AccessInstructions: Mapped[str | None] = mapped_column(Text)
    KeyLocation: Mapped[str | None] = mapped_column(String(200))
    AlarmAccessCode: Mapped[str | None] = mapped_column(String(50))
    GeneralNotes: Mapped[str | None] = mapped_column(Text)
    InspectionFrequency: Mapped[str] = mapped_column(String(30), nullable=False)
    LastInspectionDate: Mapped[date | None] = mapped_column(Date)
    NextInspectionDue: Mapped[date | None] = mapped_column(Date)
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("SYSUTCDATETIME()"))
    CreatedBy: Mapped[int | None] = mapped_column(Integer, ForeignKey("Users.UserId"))

    company: Mapped["Company"] = relationship()
    created_by_user: Mapped["User | None"] = relationship()
    # No delete-orphan cascade: Properties/Units are soft-delete only (IsActive), never hard
    # deleted through the ORM - a cascade here would be a foot-gun for a case that shouldn't
    # exist.
    units: Mapped[list["Unit"]] = relationship(back_populates="property")
