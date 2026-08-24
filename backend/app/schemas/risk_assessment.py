from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import RiskAssessmentStatus


class RiskAssessmentCreate(BaseModel):
    # PropertyId is required for a standalone assessment but ignored/overridden when
    # InspectionId/InspectionResponseId is supplied - same convention as
    # MaintenanceIssueCreate/CleaningInspectionCreate: the linked entity's own Property is
    # always the source of truth, never trusted from the client alongside it.
    PropertyId: int | None = None
    InspectionId: int | None = None
    InspectionResponseId: int | None = None
    MaintenanceIssueId: int | None = None
    Location: str | None = Field(default=None, max_length=200)
    Hazard: str = Field(min_length=1)
    WhoMayBeAffected: str | None = None
    ExistingControls: str | None = None
    Likelihood: int = Field(ge=1, le=5)
    Severity: int = Field(ge=1, le=5)
    AdditionalActionRequired: str | None = None
    ResponsiblePersonUserId: int | None = None
    TargetCompletionDate: date | None = None
    Notes: str | None = None

    # Deliberately no RiskScore/RiskLevel/Status/CompanyId fields - RiskScore is a real SQL
    # Server computed column (structurally impossible to supply, app/models/risk_assessment.py),
    # RiskLevel is derived server-side from the current risk matrix at create time, Status
    # always starts "Open", and CompanyId is always derived from the resolved Property.


class RiskAssessmentUpdate(BaseModel):
    """PATCH semantics - only supplied fields change. ONE combined update covering every
    field including Status/ResponsiblePersonUserId/TargetCompletionDate, unlike
    MaintenanceIssues' separate general-edit/assign/status endpoints - scope §19 describes no
    audit-trail requirement (unlike §18's explicit "Maintenance History") and, structurally, a
    standalone RiskAssessment may have no parent Inspection at all (InspectionId is nullable) to
    hang an ensure_can_edit-style check on - see app/services/risk_service.py's module docstring
    for the full reasoning behind this module's two-tier (not three-tier) shape."""

    Location: str | None = Field(default=None, max_length=200)
    Hazard: str | None = Field(default=None, min_length=1)
    WhoMayBeAffected: str | None = None
    ExistingControls: str | None = None
    Likelihood: int | None = Field(default=None, ge=1, le=5)
    Severity: int | None = Field(default=None, ge=1, le=5)
    AdditionalActionRequired: str | None = None
    ResponsiblePersonUserId: int | None = None
    TargetCompletionDate: date | None = None
    Status: RiskAssessmentStatus | None = None
    Notes: str | None = None

    # Likelihood/Severity ARE editable here (unlike RiskScore, which can't be set directly at
    # all) - changing either causes the service to recompute RiskLevel from the current matrix
    # at save time, the same as at create time. See risk_service.update_risk_assessment.


class RiskAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    RiskAssessmentId: int
    CompanyId: int
    PropertyId: int
    InspectionId: int | None
    InspectionResponseId: int | None
    MaintenanceIssueId: int | None
    Location: str | None
    Hazard: str
    WhoMayBeAffected: str | None
    ExistingControls: str | None
    Likelihood: int
    Severity: int
    RiskScore: int
    RiskLevel: str
    AdditionalActionRequired: str | None
    ResponsiblePersonUserId: int | None
    TargetCompletionDate: date | None
    Status: str
    Notes: str | None
    CreatedAt: datetime
