from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MeterReading(Base):
    """No CompanyId of its own and no denormalization needed (docs/DATABASE.md) - PropertyId is
    NOT NULL and directly present (unlike Units, which has neither), so isolation is a single
    join to Properties, the simplest case of any module so far.

    AIDetectedReading and ConfirmedReading are always separate columns, never conflated - scope
    §11 is explicit the AI value must never silently become the confirmed one. PhotoMediaFileId
    is a direct FK to one specific MediaFiles row (a real 1:1 "this reading's meter photo"
    relationship) rather than relying solely on the polymorphic (EntityType, EntityId) pattern
    every other media-carrying entity uses - app/services/meter_reading_service.py still creates
    that MediaFiles row through the same polymorphic mechanism (EntityType="MeterReading") for
    consistency with every other module, then stores its id here as a denormalized "primary
    photo" pointer, since a meter reading has exactly one confirmable photo, not a list of them.
    """

    __tablename__ = "MeterReadings"

    MeterReadingId: Mapped[int] = mapped_column(Integer, primary_key=True)
    InspectionResponseId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("InspectionResponses.InspectionResponseId")
    )
    PropertyId: Mapped[int] = mapped_column(Integer, ForeignKey("Properties.PropertyId"), nullable=False)
    MeterType: Mapped[str] = mapped_column(String(20), nullable=False)
    MeterSerialNumber: Mapped[str | None] = mapped_column(String(100))
    PhotoMediaFileId: Mapped[int | None] = mapped_column(Integer, ForeignKey("MediaFiles.MediaFileId"))
    AIDetectedReading: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    AIConfidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    ConfirmedReading: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    ReadingDateTime: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
    InspectorNotes: Mapped[str | None] = mapped_column(Text)
