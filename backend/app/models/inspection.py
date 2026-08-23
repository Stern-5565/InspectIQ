from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.inspection_response import InspectionResponse
    from app.models.inspection_template import InspectionTemplate
    from app.models.property import Property
    from app.models.user import User


class Inspection(Base):
    __tablename__ = "Inspections"

    InspectionId: Mapped[int] = mapped_column(Integer, primary_key=True)
    PropertyId: Mapped[int] = mapped_column(Integer, ForeignKey("Properties.PropertyId"), nullable=False)
    InspectorUserId: Mapped[int] = mapped_column(Integer, ForeignKey("Users.UserId"), nullable=False)
    InspectionTemplateId: Mapped[int] = mapped_column(
        Integer, ForeignKey("InspectionTemplates.InspectionTemplateId"), nullable=False
    )
    # Captured from InspectionTemplate.Version at start time - part of the Phase 1 §13.1
    # sign-off, lets a later session answer "which inspections predate this checklist change"
    # without full template version history.
    TemplateVersionUsed: Mapped[int] = mapped_column(Integer, nullable=False)
    InspectionType: Mapped[str | None] = mapped_column(String(50))
    InspectionDate: Mapped[date] = mapped_column(Date, nullable=False)
    StartedAt: Mapped[datetime | None] = mapped_column(DateTime)
    CompletedAt: Mapped[datetime | None] = mapped_column(DateTime)
    NextInspectionDueDate: Mapped[date | None] = mapped_column(Date)
    Status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'Scheduled'"))
    GeneralNotes: Mapped[str | None] = mapped_column(Text)
    OverallCondition: Mapped[str | None] = mapped_column(String(30))
    OverallRiskRating: Mapped[str | None] = mapped_column(String(30))
    InspectorSignaturePath: Mapped[str | None] = mapped_column(String(500))
    SubmittedAt: Mapped[datetime | None] = mapped_column(DateTime)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("SYSUTCDATETIME()"))

    property: Mapped["Property"] = relationship()
    inspector: Mapped["User"] = relationship()
    template: Mapped["InspectionTemplate"] = relationship()
    # Ordered by primary key, which is creation order - responses are created in a single
    # batch in template SortOrder when the inspection starts (app/services/inspection_service.py),
    # so InspectionResponseId order IS template order, frozen at that moment. Deliberately not
    # re-sorted via a live join to InspectionQuestion.SortOrder - that would let a later
    # template reorder silently reshuffle an already-started inspection's response order,
    # which is exactly the kind of drift the snapshot design (§13.1) exists to prevent.
    responses: Mapped[list["InspectionResponse"]] = relationship(
        back_populates="inspection", order_by="InspectionResponse.InspectionResponseId"
    )
