from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.maintenance_update import MaintenanceUpdate


class MaintenanceIssue(Base):
    __tablename__ = "MaintenanceIssues"

    MaintenanceIssueId: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Denormalized (docs/DATABASE.md §9.5/§10.1) - always derived server-side from PropertyId,
    # never accepted from the client (app/services/maintenance_service.py).
    CompanyId: Mapped[int] = mapped_column(Integer, ForeignKey("Companies.CompanyId"), nullable=False)
    PropertyId: Mapped[int] = mapped_column(Integer, ForeignKey("Properties.PropertyId"), nullable=False)
    UnitId: Mapped[int | None] = mapped_column(Integer, ForeignKey("Units.UnitId"))
    InspectionId: Mapped[int | None] = mapped_column(Integer, ForeignKey("Inspections.InspectionId"))
    InspectionResponseId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("InspectionResponses.InspectionResponseId")
    )
    Title: Mapped[str] = mapped_column(String(200), nullable=False)
    Description: Mapped[str | None] = mapped_column(Text)
    Location: Mapped[str | None] = mapped_column(String(200))
    Category: Mapped[str] = mapped_column(String(30), nullable=False)
    Priority: Mapped[str] = mapped_column(String(20), nullable=False)
    Status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'Open'"))
    AssignedUserId: Mapped[int | None] = mapped_column(Integer, ForeignKey("Users.UserId"))
    ReportedByUserId: Mapped[int] = mapped_column(Integer, ForeignKey("Users.UserId"), nullable=False)
    ReportedDate: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=text("CAST(SYSUTCDATETIME() AS DATE)")
    )
    DueDate: Mapped[date | None] = mapped_column(Date)
    CompletedDate: Mapped[date | None] = mapped_column(Date)
    Notes: Mapped[str | None] = mapped_column(Text)

    updates: Mapped[list["MaintenanceUpdate"]] = relationship(
        back_populates="issue", order_by="MaintenanceUpdate.MaintenanceUpdateId"
    )
