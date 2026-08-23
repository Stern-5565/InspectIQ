"""
Minimal Company model - just enough for the FK relationship Users needs (CompanyId is
central to auth's "company isolation" requirement). Full Company CRUD/business logic isn't
part of Phase 5 - the scope's phase list treats it as foundational data, not a standalone
phase, and Prompt 6 (Authentication) is the first module that actually needs it to exist.
"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Company(Base):
    __tablename__ = "Companies"

    CompanyId: Mapped[int] = mapped_column(Integer, primary_key=True)
    CompanyName: Mapped[str] = mapped_column(String(200), nullable=False)
    AddressLine1: Mapped[str | None] = mapped_column(String(200))
    AddressLine2: Mapped[str | None] = mapped_column(String(200))
    City: Mapped[str | None] = mapped_column(String(100))
    Postcode: Mapped[str | None] = mapped_column(String(20))
    Telephone: Mapped[str | None] = mapped_column(String(30))
    Email: Mapped[str | None] = mapped_column(String(200))
    LogoPath: Mapped[str | None] = mapped_column(String(500))
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("SYSUTCDATETIME()"))

    users: Mapped[list["User"]] = relationship(back_populates="company")
