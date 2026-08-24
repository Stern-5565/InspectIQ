from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MeterReadingUpdate(BaseModel):
    """PATCH semantics - the inspector's confirm-or-correct step (scope §11 step 4/5).
    ConfirmedReading is deliberately unvalidated against AIDetectedReading - scope is explicit
    the inspector may correct the AI value outright, not just accept or nudge it."""

    ConfirmedReading: Decimal | None = None
    MeterSerialNumber: str | None = Field(default=None, max_length=100)
    InspectorNotes: str | None = None


class MeterReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    MeterReadingId: int
    InspectionResponseId: int | None
    PropertyId: int
    MeterType: str
    MeterSerialNumber: str | None
    PhotoMediaFileId: int | None
    AIDetectedReading: Decimal | None
    AIConfidence: Decimal | None
    ConfirmedReading: Decimal | None
    ReadingDateTime: datetime
    InspectorNotes: str | None
