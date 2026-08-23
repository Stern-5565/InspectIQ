from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.inspection_section import InspectionSection
    from app.models.user import User


class InspectionTemplate(Base):
    __tablename__ = "InspectionTemplates"

    InspectionTemplateId: Mapped[int] = mapped_column(Integer, primary_key=True)
    # NULL = global default template usable by every company; non-null = a company's own
    # customized template. See docs/DATABASE.md §9.3.
    CompanyId: Mapped[int | None] = mapped_column(Integer, ForeignKey("Companies.CompanyId"))
    TemplateName: Mapped[str] = mapped_column(String(200), nullable=False)
    Description: Mapped[str | None] = mapped_column(Text)
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    Version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("SYSUTCDATETIME()"))
    CreatedBy: Mapped[int | None] = mapped_column(Integer, ForeignKey("Users.UserId"))

    company: Mapped["Company | None"] = relationship()
    created_by_user: Mapped["User | None"] = relationship()
    # Ordered by SortOrder here (not left to the caller) so every query path - list, detail,
    # future inspection-start logic - gets sections in the right order for free.
    sections: Mapped[list["InspectionSection"]] = relationship(
        back_populates="template", order_by="InspectionSection.SortOrder"
    )
