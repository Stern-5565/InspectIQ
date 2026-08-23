from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.inspection_section import InspectionSection


class InspectionQuestion(Base):
    __tablename__ = "InspectionQuestions"

    InspectionQuestionId: Mapped[int] = mapped_column(Integer, primary_key=True)
    InspectionSectionId: Mapped[int] = mapped_column(
        Integer, ForeignKey("InspectionSections.InspectionSectionId"), nullable=False
    )
    QuestionText: Mapped[str] = mapped_column(String(500), nullable=False)
    AnswerType: Mapped[str] = mapped_column(String(30), nullable=False)
    SortOrder: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    AllowNotes: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    AllowPhoto: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    RequirePhoto: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    AllowMaintenanceFlag: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    AllowRiskFlag: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    IsMandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"))
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))

    section: Mapped["InspectionSection"] = relationship(back_populates="questions")
