from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import InspectionFrequency as InspectionFrequencyEnum
from app.schemas.enums import PropertyStatus as PropertyStatusEnum
from app.schemas.enums import PropertyType as PropertyTypeEnum

# Aliased on import, not just given distinct names in enums.py: Python 3.14's lazy annotation
# evaluation (PEP 649) resolves a field's own annotation in a namespace where the class's own
# attribute name - even a bare, value-less annotation like `PropertyType: PropertyType` -
# shadows the module-level import of the same name. Confirmed by hitting a real
# "unsupported operand type(s) for |: 'NoneType' and 'NoneType'" error before adding this
# alias; not a hypothetical concern. Every schema in this module that reuses a DB column name
# matching an enum class name must alias the import the same way.


class PropertyCreate(BaseModel):
    PropertyName: str = Field(min_length=1, max_length=200)
    AddressLine1: str = Field(min_length=1, max_length=200)
    AddressLine2: str | None = Field(default=None, max_length=200)
    City: str | None = Field(default=None, max_length=100)
    Postcode: str = Field(min_length=1, max_length=20)
    PropertyType: PropertyTypeEnum
    PropertyStatus: PropertyStatusEnum = PropertyStatusEnum.ACTIVE
    NumberOfUnits: int | None = Field(default=None, ge=0)
    MainContactName: str | None = Field(default=None, max_length=200)
    MainContactPhone: str | None = Field(default=None, max_length=30)
    MainContactEmail: str | None = Field(default=None, max_length=200)
    AccessInstructions: str | None = None
    KeyLocation: str | None = Field(default=None, max_length=200)
    AlarmAccessCode: str | None = Field(default=None, max_length=50)
    GeneralNotes: str | None = None
    InspectionFrequency: InspectionFrequencyEnum
    LastInspectionDate: date | None = None
    NextInspectionDue: date | None = None

    # Deliberately no CompanyId or CreatedBy field here - both are always derived server-side
    # from the authenticated user (app/services/property_service.py), never accepted from the
    # client. See docs/DATABASE.md §10.1.


class PropertyUpdate(BaseModel):
    """All fields optional - PATCH semantics, only supplied fields are changed."""

    PropertyName: str | None = Field(default=None, min_length=1, max_length=200)
    AddressLine1: str | None = Field(default=None, min_length=1, max_length=200)
    AddressLine2: str | None = Field(default=None, max_length=200)
    City: str | None = Field(default=None, max_length=100)
    Postcode: str | None = Field(default=None, min_length=1, max_length=20)
    PropertyType: PropertyTypeEnum | None = None
    PropertyStatus: PropertyStatusEnum | None = None
    NumberOfUnits: int | None = Field(default=None, ge=0)
    MainContactName: str | None = Field(default=None, max_length=200)
    MainContactPhone: str | None = Field(default=None, max_length=30)
    MainContactEmail: str | None = Field(default=None, max_length=200)
    AccessInstructions: str | None = None
    KeyLocation: str | None = Field(default=None, max_length=200)
    AlarmAccessCode: str | None = Field(default=None, max_length=50)
    GeneralNotes: str | None = None
    InspectionFrequency: InspectionFrequencyEnum | None = None
    LastInspectionDate: date | None = None
    NextInspectionDue: date | None = None


class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    PropertyId: int
    CompanyId: int
    PropertyName: str
    AddressLine1: str
    AddressLine2: str | None
    City: str | None
    Postcode: str
    PropertyType: str
    PropertyStatus: str
    NumberOfUnits: int | None
    MainContactName: str | None
    MainContactPhone: str | None
    MainContactEmail: str | None
    AccessInstructions: str | None
    KeyLocation: str | None
    AlarmAccessCode: str | None
    GeneralNotes: str | None
    InspectionFrequency: str
    LastInspectionDate: date | None
    NextInspectionDue: date | None
    IsActive: bool
    CreatedAt: datetime
    CreatedBy: int | None
