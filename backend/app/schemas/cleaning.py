from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import CleaningAreaType, CleaningGrade, CleaningInspectionStatus


class CleaningAreaCreate(BaseModel):
    AreaName: str = Field(min_length=1, max_length=100)
    AreaType: CleaningAreaType

    # PropertyId comes from the URL path (/api/properties/{property_id}/cleaning-areas), same
    # convention as UnitCreate.


class CleaningAreaUpdate(BaseModel):
    AreaName: str | None = Field(default=None, min_length=1, max_length=100)
    AreaType: CleaningAreaType | None = None
    IsActive: bool | None = None


class CleaningAreaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    CleaningAreaId: int
    PropertyId: int
    AreaName: str
    AreaType: str
    IsActive: bool


class CleaningInspectionCreate(BaseModel):
    CleaningAreaId: int
    Grade: CleaningGrade
    Notes: str | None = None
    CleaningRequired: bool = False
    Urgent: bool = False
    AssignedUserId: int | None = None
    DueDate: date | None = None

    # InspectionId comes from the URL path (/api/inspections/{inspection_id}/cleaning).
    # Deliberately no Status field - starts "Pending", or "Assigned" if AssignedUserId is
    # supplied (app/services/cleaning_service.py), matching MaintenanceIssueCreate's exact
    # convention for the same reason.


class CleaningInspectionUpdate(BaseModel):
    """PATCH semantics - only supplied fields are changed. One combined update endpoint, not
    split into general-edit/assign/status like MaintenanceIssues - scope §16 describes cleaning
    grading as a single flat record with no audit-trail requirement (unlike §18's explicit
    "Maintenance History" timeline), so a simpler shape is proportionate here rather than
    copying Maintenance's three-endpoint pattern by default. See
    app/services/cleaning_service.py's module docstring for the full comparison."""

    Grade: CleaningGrade | None = None
    Notes: str | None = None
    CleaningRequired: bool | None = None
    Urgent: bool | None = None
    AssignedUserId: int | None = None
    DueDate: date | None = None
    Status: CleaningInspectionStatus | None = None


class CleaningInspectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    CleaningInspectionId: int
    InspectionId: int
    CleaningAreaId: int
    Grade: str
    Notes: str | None
    CleaningRequired: bool
    Urgent: bool
    AssignedUserId: int | None
    DueDate: date | None
    Status: str
