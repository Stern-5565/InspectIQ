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


class MeterReadingSummaryResponse(MeterReadingResponse):
    """The standalone Meter Readings module's own shape (list + single detail) - adds
    PropertyName/InspectionId, neither a real column on MeterReading itself. PropertyName is
    reached via Property; InspectionId via an OUTER join through InspectionResponse (None for a
    standalone reading with no InspectionResponseId at all - a real, valid state, not a failed
    lookup). Built explicitly via from_row, never `.model_validate()` on a bare MeterReading -
    matching CleaningInspectionSummaryResponse/VacantUnitInspectionSummaryResponse's exact
    convention."""

    PropertyName: str
    InspectionId: int | None

    @classmethod
    def from_row(cls, reading, property_name: str, inspection_id: int | None) -> "MeterReadingSummaryResponse":
        return cls(
            MeterReadingId=reading.MeterReadingId,
            InspectionResponseId=reading.InspectionResponseId,
            PropertyId=reading.PropertyId,
            MeterType=reading.MeterType,
            MeterSerialNumber=reading.MeterSerialNumber,
            PhotoMediaFileId=reading.PhotoMediaFileId,
            AIDetectedReading=reading.AIDetectedReading,
            AIConfidence=reading.AIConfidence,
            ConfirmedReading=reading.ConfirmedReading,
            ReadingDateTime=reading.ReadingDateTime,
            InspectorNotes=reading.InspectorNotes,
            PropertyName=property_name,
            InspectionId=inspection_id,
        )
