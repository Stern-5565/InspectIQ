from datetime import date

from pydantic import BaseModel

# Field names match the column aliases in database/reports/15_DashboardQueries.sql and
# app/repositories/dashboard_repository.py directly - these responses aren't built from a
# single ORM entity (a dashboard metric isn't a row in any one table), so there's no
# from_attributes/model_validate(orm_obj) the way every other module's Response schema works.


class InspectionsSummary(BaseModel):
    DueToday: int
    DueThisWeek: int
    Overdue: int
    CompletedThisMonth: int


class MaintenanceSummary(BaseModel):
    OpenCount: int
    HighPriority: int
    UrgentOrEmergency: int
    OverdueCount: int


class RisksSummary(BaseModel):
    CriticalCount: int
    HighCount: int
    OutstandingCount: int


class CleaningSummary(BaseModel):
    GradeAOrB: int
    GradeC: int
    GradeDOrE: int


class PropertiesSummary(BaseModel):
    TotalActiveProperties: int
    PropertiesRequiringAttention: int


class RecentInspection(BaseModel):
    InspectionId: int
    PropertyName: str
    InspectorName: str
    Status: str
    InspectionDate: date


class RecentMaintenanceIssue(BaseModel):
    MaintenanceIssueId: int
    PropertyName: str
    Title: str
    Priority: str
    Status: str
    ReportedDate: date


class RecentRiskAssessment(BaseModel):
    RiskAssessmentId: int
    PropertyName: str
    Hazard: str
    RiskLevel: str
    RiskScore: int


class RecentActivity(BaseModel):
    Inspections: list[RecentInspection]
    MaintenanceIssues: list[RecentMaintenanceIssue]
    RiskAssessments: list[RecentRiskAssessment]


class DashboardResponse(BaseModel):
    Inspections: InspectionsSummary
    Maintenance: MaintenanceSummary
    Risks: RisksSummary
    Cleaning: CleaningSummary
    Properties: PropertiesSummary
    RecentActivity: RecentActivity
