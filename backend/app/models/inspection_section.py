from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.inspection_question import InspectionQuestion
    from app.models.inspection_template import InspectionTemplate


class InspectionSection(Base):
    __tablename__ = "InspectionSections"

    InspectionSectionId: Mapped[int] = mapped_column(Integer, primary_key=True)
    InspectionTemplateId: Mapped[int] = mapped_column(
        Integer, ForeignKey("InspectionTemplates.InspectionTemplateId"), nullable=False
    )
    SectionName: Mapped[str] = mapped_column(String(200), nullable=False)
    SortOrder: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))

    template: Mapped["InspectionTemplate"] = relationship(back_populates="sections")
    questions: Mapped[list["InspectionQuestion"]] = relationship(
        back_populates="section", order_by="InspectionQuestion.SortOrder"
    )
