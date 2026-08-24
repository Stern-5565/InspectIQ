from sqlalchemy import Boolean, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CleaningArea(Base):
    """Per-property configurable list, not a fixed global enum (docs/DATABASE.md) - a block
    with a lift and bin store needs different areas than an HMO without either. A new
    property's default set (Entrance/Hallway/BinArea) is auto-seeded by
    app/services/cleaning_service.seed_default_areas_for_property, called from
    property_service.create_property - see that function's comment for why (docs/DATABASE.md
    §10's "Possible Problems" flagged an unconfigured property as a real onboarding gap)."""

    __tablename__ = "CleaningAreas"

    CleaningAreaId: Mapped[int] = mapped_column(Integer, primary_key=True)
    PropertyId: Mapped[int] = mapped_column(Integer, ForeignKey("Properties.PropertyId"), nullable=False)
    AreaName: Mapped[str] = mapped_column(String(100), nullable=False)
    AreaType: Mapped[str] = mapped_column(String(30), nullable=False)
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
