from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import MaintenanceCategory, MaintenanceIssueStatus, MaintenancePriority


class MaintenanceIssueCreate(BaseModel):
    # PropertyId is required for a manual issue but ignored/overridden when InspectionResponseId
    # is supplied - see app/services/maintenance_service.py's create_issue: the response's own
    # Inspection is the source of truth for Property/Inspection linkage, never trusted from the
    # client alongside a response_id (a mismatched pair would be a real cross-property/tenant
    # data-integrity bug, not just an inconsistency).
    PropertyId: int | None = None
    UnitId: int | None = None
    InspectionId: int | None = None
    InspectionResponseId: int | None = None
    Title: str = Field(min_length=1, max_length=200)
    Description: str | None = None
    # Auto-filled from the response's SectionNameSnapshot/QuestionTextSnapshot when created from
    # an inspection response and not explicitly supplied (scope §17: "automatically copying...
    # Inspection section, Checklist item"). Stored as plain text here rather than duplicating the
    # section/question snapshot columns onto MaintenanceIssues itself - docs/DATABASE.md
    # deliberately didn't add those, since InspectionResponseId is already a stable FK back to
    # them for anything needing the authoritative source (e.g. a report).
    Location: str | None = Field(default=None, max_length=200)
    Category: MaintenanceCategory
    Priority: MaintenancePriority = MaintenancePriority.MEDIUM
    AssignedUserId: int | None = None
    DueDate: date | None = None
    Notes: str | None = None

    # Deliberately no CompanyId, ReportedByUserId, ReportedDate, or Status - CompanyId/
    # ReportedByUserId are always derived server-side (docs/DATABASE.md §10.1), ReportedDate
    # defaults to today at the DB layer, and a new issue always starts "Open" - status changes
    # only ever happen through the dedicated status-update endpoint, never as part of create.


class MaintenanceIssueUpdate(BaseModel):
    """PATCH semantics for the issue's own descriptive fields - Admin/Manager only
    (app/services/maintenance_service.py). Deliberately excludes Status/AssignedUserId, which
    have their own dedicated endpoints (same "dedicated action, not folded into a generic PATCH"
    pattern as Unit's occupancy-status change, app/schemas/unit.py)."""

    Title: str | None = Field(default=None, min_length=1, max_length=200)
    Description: str | None = None
    Location: str | None = Field(default=None, max_length=200)
    Category: MaintenanceCategory | None = None
    Priority: MaintenancePriority | None = None
    DueDate: date | None = None
    Notes: str | None = None


class MaintenanceStatusUpdate(BaseModel):
    NewStatus: MaintenanceIssueStatus
    Comment: str | None = None


class MaintenanceAssignmentUpdate(BaseModel):
    AssignedUserId: int


class MaintenanceNoteCreate(BaseModel):
    Comment: str = Field(min_length=1)


class MaintenanceUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    MaintenanceUpdateId: int
    UpdateType: str
    OldStatus: str | None
    NewStatus: str | None
    Comment: str | None
    UserId: int
    CreatedAt: datetime


class MaintenanceIssueSummaryResponse(BaseModel):
    """List view - matches the established pattern (Properties, Inspections): list is cheap, no
    timeline; detail is where the full history lives."""

    model_config = ConfigDict(from_attributes=True)

    MaintenanceIssueId: int
    PropertyId: int
    UnitId: int | None
    Title: str
    Category: str
    Priority: str
    Status: str
    AssignedUserId: int | None
    ReportedByUserId: int
    ReportedDate: date
    DueDate: date | None


class MaintenanceIssueDetailResponse(BaseModel):
    # No from_attributes/model_validate(issue) here on purpose - the ORM relationship is named
    # `updates` (lowercase, matching this codebase's relationship-naming convention) while this
    # schema field is `Updates` (matching every other PascalCase column), and Pydantic's
    # from_attributes does an exact attribute-name lookup, not a case-insensitive one. Built
    # explicitly via from_issue() instead, the same pattern InspectionDetailResponse.from_inspection
    # already uses for its own nested Sections list.
    MaintenanceIssueId: int
    CompanyId: int
    PropertyId: int
    UnitId: int | None
    InspectionId: int | None
    InspectionResponseId: int | None
    Title: str
    Description: str | None
    Location: str | None
    Category: str
    Priority: str
    Status: str
    AssignedUserId: int | None
    ReportedByUserId: int
    ReportedDate: date
    DueDate: date | None
    CompletedDate: date | None
    Notes: str | None
    Updates: list[MaintenanceUpdateResponse]

    @classmethod
    def from_issue(cls, issue, updates: list) -> "MaintenanceIssueDetailResponse":
        return cls(
            MaintenanceIssueId=issue.MaintenanceIssueId,
            CompanyId=issue.CompanyId,
            PropertyId=issue.PropertyId,
            UnitId=issue.UnitId,
            InspectionId=issue.InspectionId,
            InspectionResponseId=issue.InspectionResponseId,
            Title=issue.Title,
            Description=issue.Description,
            Location=issue.Location,
            Category=issue.Category,
            Priority=issue.Priority,
            Status=issue.Status,
            AssignedUserId=issue.AssignedUserId,
            ReportedByUserId=issue.ReportedByUserId,
            ReportedDate=issue.ReportedDate,
            DueDate=issue.DueDate,
            CompletedDate=issue.CompletedDate,
            Notes=issue.Notes,
            Updates=[MaintenanceUpdateResponse.model_validate(u) for u in updates],
        )
