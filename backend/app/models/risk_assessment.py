from datetime import date, datetime

from sqlalchemy import Computed, Date, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RiskAssessment(Base):
    """CompanyId denormalized (docs/DATABASE.md §9.5), always derived server-side from
    PropertyId, never accepted from the client (app/services/risk_service.py).

    RiskScore is mapped with `Computed(...)`, not a plain column - it's a real SQL Server
    `PERSISTED` computed column (`Likelihood * Severity`), so a client-supplied score is
    structurally impossible, not just disallowed by app convention (scope §14/§19). `Computed`
    tells SQLAlchemy to exclude this column from generated INSERT/UPDATE statements automatically
    (attempting to set it would be rejected by SQL Server anyway) - the repository's
    `db.refresh()` after insert is what actually populates it back onto the Python object.

    RiskLevel, by contrast, is a plain snapshot column, not computed - its source
    (RiskMatrixLevels) is itself editable, so it's written once at create time from whichever
    band currently matches the score, the same historical-accuracy principle as
    InspectionResponses' snapshot columns (§13.1) - thresholds can change later without
    reclassifying old assessments.
    """

    __tablename__ = "RiskAssessments"

    RiskAssessmentId: Mapped[int] = mapped_column(Integer, primary_key=True)
    CompanyId: Mapped[int] = mapped_column(Integer, ForeignKey("Companies.CompanyId"), nullable=False)
    PropertyId: Mapped[int] = mapped_column(Integer, ForeignKey("Properties.PropertyId"), nullable=False)
    InspectionId: Mapped[int | None] = mapped_column(Integer, ForeignKey("Inspections.InspectionId"))
    InspectionResponseId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("InspectionResponses.InspectionResponseId")
    )
    MaintenanceIssueId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("MaintenanceIssues.MaintenanceIssueId")
    )
    Location: Mapped[str | None] = mapped_column(String(200))
    Hazard: Mapped[str] = mapped_column(Text, nullable=False)
    WhoMayBeAffected: Mapped[str | None] = mapped_column(Text)
    ExistingControls: Mapped[str | None] = mapped_column(Text)
    Likelihood: Mapped[int] = mapped_column(Integer, nullable=False)
    Severity: Mapped[int] = mapped_column(Integer, nullable=False)
    RiskScore: Mapped[int] = mapped_column(Integer, Computed("Likelihood * Severity", persisted=True))
    RiskLevel: Mapped[str] = mapped_column(String(20), nullable=False)
    AdditionalActionRequired: Mapped[str | None] = mapped_column(Text)
    ResponsiblePersonUserId: Mapped[int | None] = mapped_column(Integer, ForeignKey("Users.UserId"))
    TargetCompletionDate: Mapped[date | None] = mapped_column(Date)
    Status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'Open'"))
    Notes: Mapped[str | None] = mapped_column(Text)
    CreatedAt: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
