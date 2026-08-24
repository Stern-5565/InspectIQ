from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.maintenance_issue import MaintenanceIssue


class MaintenanceUpdate(Base):
    """One row per timeline entry (scope §18) - written by the service layer on every status
    change, comment, or photo upload, never reconstructed from other tables after the fact."""

    __tablename__ = "MaintenanceUpdates"

    MaintenanceUpdateId: Mapped[int] = mapped_column(Integer, primary_key=True)
    MaintenanceIssueId: Mapped[int] = mapped_column(
        Integer, ForeignKey("MaintenanceIssues.MaintenanceIssueId"), nullable=False
    )
    UpdateType: Mapped[str] = mapped_column(String(30), nullable=False)
    OldStatus: Mapped[str | None] = mapped_column(String(20))
    NewStatus: Mapped[str | None] = mapped_column(String(20))
    Comment: Mapped[str | None] = mapped_column(Text)
    UserId: Mapped[int] = mapped_column(Integer, ForeignKey("Users.UserId"), nullable=False)
    CreatedAt: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )

    issue: Mapped["MaintenanceIssue"] = relationship(back_populates="updates")
