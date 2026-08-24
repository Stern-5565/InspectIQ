"""Dashboard (Phase 15, scope §23).

View-only, any company member - a dashboard has no natural "mutate" action of its own, the
same reasoning applied to every read side of every other module. No new authorization design
here: this phase is genuinely thinner than any since Phase 7, since every underlying query was
already written and proven in Phase 2 (database/reports/15_DashboardQueries.sql) - this module's
only job is running each one scoped to current_user.CompanyId (never client input, same rule as
everywhere else in this project) and shaping the combined response.
"""
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories import dashboard_repository as repo
from app.schemas.dashboard import (
    CleaningSummary,
    DashboardResponse,
    InspectionsSummary,
    MaintenanceSummary,
    PropertiesSummary,
    RecentActivity,
    RecentInspection,
    RecentMaintenanceIssue,
    RecentRiskAssessment,
    RisksSummary,
)


def get_dashboard(db: Session, current_user: User) -> DashboardResponse:
    company_id = current_user.CompanyId

    due_counts = repo.get_inspection_due_counts(db, company_id)
    completed_this_month = repo.get_inspections_completed_this_month(db, company_id)
    maintenance = repo.get_maintenance_summary(db, company_id)
    risks = repo.get_risk_summary(db, company_id)
    cleaning = repo.get_cleaning_grade_summary(db, company_id)
    properties = repo.get_properties_summary(db, company_id)

    return DashboardResponse(
        Inspections=InspectionsSummary(**due_counts, CompletedThisMonth=completed_this_month),
        Maintenance=MaintenanceSummary(**maintenance),
        Risks=RisksSummary(**risks),
        Cleaning=CleaningSummary(**cleaning),
        Properties=PropertiesSummary(**properties),
        RecentActivity=RecentActivity(
            Inspections=[RecentInspection(**row) for row in repo.get_recent_inspections(db, company_id)],
            MaintenanceIssues=[
                RecentMaintenanceIssue(**row) for row in repo.get_recent_maintenance_issues(db, company_id)
            ],
            RiskAssessments=[
                RecentRiskAssessment(**row) for row in repo.get_recent_high_risk_assessments(db, company_id)
            ],
        ),
    )
