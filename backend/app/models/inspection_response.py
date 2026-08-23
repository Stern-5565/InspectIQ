from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, Date, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.inspection_question import InspectionQuestion


class InspectionResponse(Base):
    __tablename__ = "InspectionResponses"

    InspectionResponseId: Mapped[int] = mapped_column(Integer, primary_key=True)
    InspectionId: Mapped[int] = mapped_column(Integer, ForeignKey("Inspections.InspectionId"), nullable=False)
    # Kept for analytics/reporting joins ONLY - never used to render a response's displayed
    # content, which always comes from the *Snapshot columns below (docs/DATABASE.md §4).
    InspectionQuestionId: Mapped[int] = mapped_column(
        Integer, ForeignKey("InspectionQuestions.InspectionQuestionId"), nullable=False
    )
    QuestionTextSnapshot: Mapped[str] = mapped_column(String(500), nullable=False)
    SectionNameSnapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    AnswerTypeSnapshot: Mapped[str] = mapped_column(String(30), nullable=False)
    # Canonical human-readable value, always populated regardless of AnswerTypeSnapshot -
    # AnswerNumber/AnswerDate exist alongside it only for type-safe querying, not as the
    # primary display source (docs/DATABASE.md §9.4).
    AnswerText: Mapped[str | None] = mapped_column(Text)
    AnswerNumber: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    AnswerDate: Mapped[date | None] = mapped_column(Date)
    IsNotApplicable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    Notes: Mapped[str | None] = mapped_column(Text)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("SYSUTCDATETIME()"))
    UpdatedAt: Mapped[datetime | None] = mapped_column(DateTime)

    inspection: Mapped["Inspection"] = relationship(back_populates="responses")
    question: Mapped["InspectionQuestion"] = relationship()
