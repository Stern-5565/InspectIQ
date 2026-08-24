from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class VacantUnitInspectionCreate(BaseModel):
    UnitId: int
    DateIdentifiedVacant: date | None = None  # defaults to today if not supplied
    Condition: str | None = Field(default=None, max_length=30)
    # Genuinely optional/tri-state (None = not checked), not defaulting to False - matches the
    # DB columns, which are nullable BIT with no DEFAULT (app/models/vacant_unit_inspection.py).
    ElectricityOn: bool | None = None
    WaterOn: bool | None = None
    HeatingWorking: bool | None = None
    WindowsSecure: bool | None = None
    DoorsSecure: bool | None = None
    SignsOfLeaks: bool | None = None
    SignsOfDamp: bool | None = None
    SignsOfPests: bool | None = None
    CleaningRequired: bool | None = None
    WasteItemsLeftBehind: bool | None = None
    MaintenanceRequired: bool | None = None
    Notes: str | None = None

    # Deliberately no UnitId-belongs-to-property trust here beyond what the service checks -
    # InspectionId comes from the URL path (/api/inspections/{inspection_id}/vacant-unit-
    # inspections), same convention as CleaningInspectionCreate.


class VacantUnitInspectionUpdate(BaseModel):
    """PATCH semantics - only supplied fields change. UnitId is deliberately excluded (the
    record shouldn't be silently reassigned to a different unit after creation), same
    convention as InspectionResponseUpdate excluding InspectionQuestionId."""

    DateIdentifiedVacant: date | None = None
    Condition: str | None = Field(default=None, max_length=30)
    ElectricityOn: bool | None = None
    WaterOn: bool | None = None
    HeatingWorking: bool | None = None
    WindowsSecure: bool | None = None
    DoorsSecure: bool | None = None
    SignsOfLeaks: bool | None = None
    SignsOfDamp: bool | None = None
    SignsOfPests: bool | None = None
    CleaningRequired: bool | None = None
    WasteItemsLeftBehind: bool | None = None
    MaintenanceRequired: bool | None = None
    Notes: str | None = None


class VacantUnitInspectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    VacantUnitInspectionId: int
    InspectionId: int
    UnitId: int
    DateIdentifiedVacant: date
    Condition: str | None
    ElectricityOn: bool | None
    WaterOn: bool | None
    HeatingWorking: bool | None
    WindowsSecure: bool | None
    DoorsSecure: bool | None
    SignsOfLeaks: bool | None
    SignsOfDamp: bool | None
    SignsOfPests: bool | None
    CleaningRequired: bool | None
    WasteItemsLeftBehind: bool | None
    MaintenanceRequired: bool | None
    Notes: str | None
    CreatedAt: datetime
