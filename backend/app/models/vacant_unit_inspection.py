from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VacantUnitInspection(Base):
    """Its own table, not a generic InspectionResponse (scope §13, docs/DATABASE.md) - stores
    history without overwriting the unit's current status, and the field set (electricity/
    water/heating on-off etc.) doesn't fit the generic Yes/No/Text/Number answer shape. No
    Status/AssignedUserId columns exist here, unlike MaintenanceIssues/CleaningInspections -
    this is a one-time recorded finding, not its own follow-up workflow; any required
    maintenance/cleaning work spawns its own MaintenanceIssue/CleaningInspection record instead
    (app/services/vacant_unit_service.py's module docstring)."""

    __tablename__ = "VacantUnitInspections"

    VacantUnitInspectionId: Mapped[int] = mapped_column(Integer, primary_key=True)
    InspectionId: Mapped[int] = mapped_column(Integer, ForeignKey("Inspections.InspectionId"), nullable=False)
    UnitId: Mapped[int] = mapped_column(Integer, ForeignKey("Units.UnitId"), nullable=False)
    DateIdentifiedVacant: Mapped[date] = mapped_column(Date, nullable=False)
    Condition: Mapped[str | None] = mapped_column(String(30))
    # Every BIT column below is nullable with NO database default (unlike, say,
    # MaintenanceIssues.CleaningRequired, which defaults to 0) - NULL is a deliberate, distinct
    # "not checked/not recorded" state here, not the same as False. Kept nullable through the
    # ORM and the Pydantic schemas rather than defaulting to False in the app layer, which would
    # silently misreport "checked and confirmed off" for something the inspector simply skipped.
    ElectricityOn: Mapped[bool | None] = mapped_column(Boolean)
    WaterOn: Mapped[bool | None] = mapped_column(Boolean)
    HeatingWorking: Mapped[bool | None] = mapped_column(Boolean)
    WindowsSecure: Mapped[bool | None] = mapped_column(Boolean)
    DoorsSecure: Mapped[bool | None] = mapped_column(Boolean)
    SignsOfLeaks: Mapped[bool | None] = mapped_column(Boolean)
    SignsOfDamp: Mapped[bool | None] = mapped_column(Boolean)
    SignsOfPests: Mapped[bool | None] = mapped_column(Boolean)
    CleaningRequired: Mapped[bool | None] = mapped_column(Boolean)
    WasteItemsLeftBehind: Mapped[bool | None] = mapped_column(Boolean)
    MaintenanceRequired: Mapped[bool | None] = mapped_column(Boolean)
    Notes: Mapped[str | None] = mapped_column(Text)
    CreatedAt: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
