from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.property import Property


class Unit(Base):
    __tablename__ = "Units"

    UnitId: Mapped[int] = mapped_column(Integer, primary_key=True)
    PropertyId: Mapped[int] = mapped_column(Integer, ForeignKey("Properties.PropertyId"), nullable=False)
    UnitNumber: Mapped[str] = mapped_column(String(50), nullable=False)
    Floor: Mapped[str | None] = mapped_column(String(30))
    OccupancyStatus: Mapped[str] = mapped_column(String(30), nullable=False)
    TenantOccupierName: Mapped[str | None] = mapped_column(String(200))
    Notes: Mapped[str | None] = mapped_column(Text)
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("SYSUTCDATETIME()"))

    property: Mapped["Property"] = relationship(back_populates="units")
