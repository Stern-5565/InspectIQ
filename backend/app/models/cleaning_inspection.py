from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CleaningInspection(Base):
    """One graded record per communal area per inspection (scope §16). `InspectionId` is
    NOT NULL - unlike MaintenanceIssues, a cleaning grade always originates from conducting a
    real Inspection, never created standalone (docs/DATABASE.md's own table sketch)."""

    __tablename__ = "CleaningInspections"

    CleaningInspectionId: Mapped[int] = mapped_column(Integer, primary_key=True)
    InspectionId: Mapped[int] = mapped_column(Integer, ForeignKey("Inspections.InspectionId"), nullable=False)
    CleaningAreaId: Mapped[int] = mapped_column(
        Integer, ForeignKey("CleaningAreas.CleaningAreaId"), nullable=False
    )
    Grade: Mapped[str] = mapped_column(String(1), nullable=False)
    Notes: Mapped[str | None] = mapped_column(Text)
    CleaningRequired: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    Urgent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    AssignedUserId: Mapped[int | None] = mapped_column(Integer, ForeignKey("Users.UserId"))
    DueDate: Mapped[date | None] = mapped_column(Date)
    Status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'Pending'"))
