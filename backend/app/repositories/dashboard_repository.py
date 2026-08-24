"""DB access only - no business rules.

Each function here mirrors one query block in database/reports/15_DashboardQueries.sql - that
file's own header comment says it was written back in Phase 2 specifically "to be lifted
directly into DashboardRepository methods in Phase 15." Every function takes company_id
directly (never resolves it itself) and returns plain dicts/RowMappings, not ORM entities - a
dashboard metric isn't a row in any one table.

SUM() over zero matching rows returns NULL, not 0, in SQL Server - every aggregate here is
coalesced with `or 0` in Python, the same ISNULL(...) rule documented throughout
database/reports/15_DashboardQueries.sql and docs/AI_HANDOFF.md.
"""
from datetime import date, timedelta

from sqlalchemy import RowMapping, case, func, select
from sqlalchemy.orm import Session

from app.models.cleaning_area import CleaningArea
from app.models.cleaning_inspection import CleaningInspection
from app.models.inspection import Inspection
from app.models.maintenance_issue import MaintenanceIssue
from app.models.property import Property
from app.models.risk_assessment import RiskAssessment
from app.models.user import User

_OPEN_MAINTENANCE = MaintenanceIssue.Status.not_in(("Completed", "Closed"))
_ACTIVE_RISK = RiskAssessment.Status.in_(("Open", "ActionPlanned"))


def get_inspection_due_counts(db: Session, company_id: int) -> dict[str, int]:
    today = date.today()
    week_end = today + timedelta(days=7)
    stmt = select(
        func.sum(case((Property.NextInspectionDue == today, 1), else_=0)).label("DueToday"),
        func.sum(
            case(
                ((Property.NextInspectionDue > today) & (Property.NextInspectionDue <= week_end), 1),
                else_=0,
            )
        ).label("DueThisWeek"),
        func.sum(case((Property.NextInspectionDue < today, 1), else_=0)).label("Overdue"),
    ).where(
        Property.CompanyId == company_id,
        Property.IsActive == True,  # noqa: E712 - SQLAlchemy needs `== True`, not `is True`
        Property.NextInspectionDue.is_not(None),
    )
    row = db.execute(stmt).mappings().one()
    return {key: value or 0 for key, value in row.items()}


def get_inspections_completed_this_month(db: Session, company_id: int) -> int:
    today = date.today()
    month_start = today.replace(day=1)
    stmt = (
        select(func.count())
        .select_from(Inspection)
        .join(Property, Property.PropertyId == Inspection.PropertyId)
        .where(
            Property.CompanyId == company_id,
            Inspection.Status.in_(("Completed", "Submitted")),
            Inspection.CompletedAt >= month_start,
        )
    )
    return db.execute(stmt).scalar_one()


def get_maintenance_summary(db: Session, company_id: int) -> dict[str, int]:
    today = date.today()
    stmt = select(
        func.sum(case((_OPEN_MAINTENANCE, 1), else_=0)).label("OpenCount"),
        func.sum(case((_OPEN_MAINTENANCE & (MaintenanceIssue.Priority == "High"), 1), else_=0)).label(
            "HighPriority"
        ),
        func.sum(
            case((_OPEN_MAINTENANCE & MaintenanceIssue.Priority.in_(("Urgent", "Emergency")), 1), else_=0)
        ).label("UrgentOrEmergency"),
        func.sum(case((_OPEN_MAINTENANCE & (MaintenanceIssue.DueDate < today), 1), else_=0)).label(
            "OverdueCount"
        ),
    ).where(MaintenanceIssue.CompanyId == company_id)
    row = db.execute(stmt).mappings().one()
    return {key: value or 0 for key, value in row.items()}


def get_risk_summary(db: Session, company_id: int) -> dict[str, int]:
    stmt = select(
        func.sum(case((_ACTIVE_RISK & (RiskAssessment.RiskLevel == "Critical"), 1), else_=0)).label(
            "CriticalCount"
        ),
        func.sum(case((_ACTIVE_RISK & (RiskAssessment.RiskLevel == "High"), 1), else_=0)).label("HighCount"),
        func.sum(case((_ACTIVE_RISK, 1), else_=0)).label("OutstandingCount"),
    ).where(RiskAssessment.CompanyId == company_id)
    row = db.execute(stmt).mappings().one()
    return {key: value or 0 for key, value in row.items()}


def get_cleaning_grade_summary(db: Session, company_id: int) -> dict[str, int]:
    """"Current" grade per area is its most recent CleaningInspection (a point-in-time
    assessment, not a stored current-state column - docs/DATABASE.md §5), so the latest one per
    area is picked with ROW_NUMBER(), same as the raw SQL this mirrors."""
    latest = (
        select(
            CleaningInspection.Grade,
            func.row_number()
            .over(
                partition_by=CleaningInspection.CleaningAreaId,
                order_by=(Inspection.InspectionDate.desc(), CleaningInspection.CleaningInspectionId.desc()),
            )
            .label("rn"),
        )
        .join(CleaningArea, CleaningArea.CleaningAreaId == CleaningInspection.CleaningAreaId)
        .join(Inspection, Inspection.InspectionId == CleaningInspection.InspectionId)
        .join(Property, Property.PropertyId == CleaningArea.PropertyId)
        .where(Property.CompanyId == company_id)
        .subquery()
    )
    stmt = select(
        func.sum(case((latest.c.Grade.in_(("A", "B")), 1), else_=0)).label("GradeAOrB"),
        func.sum(case((latest.c.Grade == "C", 1), else_=0)).label("GradeC"),
        func.sum(case((latest.c.Grade.in_(("D", "E")), 1), else_=0)).label("GradeDOrE"),
    ).where(latest.c.rn == 1)
    row = db.execute(stmt).mappings().one()
    return {key: value or 0 for key, value in row.items()}


def get_properties_summary(db: Session, company_id: int) -> dict[str, int]:
    """"Requiring attention" is a rollup, not a stored flag - an active property with an
    overdue inspection, an open Urgent/Emergency maintenance issue, or an open Critical risk.
    Deliberately excludes cleaning grade (see database/reports/15_DashboardQueries.sql's own
    comment) to avoid double-alerting alongside the Cleaning card."""
    today = date.today()
    total_active = db.execute(
        select(func.count())
        .select_from(Property)
        .where(Property.CompanyId == company_id, Property.IsActive == True)  # noqa: E712
    ).scalar_one()

    urgent_maintenance_properties = select(MaintenanceIssue.PropertyId).where(
        _OPEN_MAINTENANCE, MaintenanceIssue.Priority.in_(("Urgent", "Emergency"))
    )
    critical_risk_properties = select(RiskAssessment.PropertyId).where(
        _ACTIVE_RISK, RiskAssessment.RiskLevel == "Critical"
    )
    requiring_attention = db.execute(
        select(func.count(func.distinct(Property.PropertyId))).where(
            Property.CompanyId == company_id,
            Property.IsActive == True,  # noqa: E712
            (Property.NextInspectionDue.is_not(None) & (Property.NextInspectionDue < today))
            | Property.PropertyId.in_(urgent_maintenance_properties)
            | Property.PropertyId.in_(critical_risk_properties),
        )
    ).scalar_one()

    return {"TotalActiveProperties": total_active, "PropertiesRequiringAttention": requiring_attention}


def get_recent_inspections(db: Session, company_id: int, limit: int = 10) -> list[RowMapping]:
    stmt = (
        select(
            Inspection.InspectionId,
            Property.PropertyName,
            User.FirstName.concat(" ").concat(User.LastName).label("InspectorName"),
            Inspection.Status,
            Inspection.InspectionDate,
        )
        .join(Property, Property.PropertyId == Inspection.PropertyId)
        .join(User, User.UserId == Inspection.InspectorUserId)
        .where(Property.CompanyId == company_id)
        .order_by(Inspection.InspectionDate.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).mappings().all())


def get_recent_maintenance_issues(db: Session, company_id: int, limit: int = 10) -> list[RowMapping]:
    stmt = (
        select(
            MaintenanceIssue.MaintenanceIssueId,
            Property.PropertyName,
            MaintenanceIssue.Title,
            MaintenanceIssue.Priority,
            MaintenanceIssue.Status,
            MaintenanceIssue.ReportedDate,
        )
        .join(Property, Property.PropertyId == MaintenanceIssue.PropertyId)
        .where(MaintenanceIssue.CompanyId == company_id, _OPEN_MAINTENANCE)
        .order_by(MaintenanceIssue.ReportedDate.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).mappings().all())


def get_recent_high_risk_assessments(db: Session, company_id: int, limit: int = 10) -> list[RowMapping]:
    stmt = (
        select(
            RiskAssessment.RiskAssessmentId,
            Property.PropertyName,
            RiskAssessment.Hazard,
            RiskAssessment.RiskLevel,
            RiskAssessment.RiskScore,
        )
        .join(Property, Property.PropertyId == RiskAssessment.PropertyId)
        .where(
            RiskAssessment.CompanyId == company_id,
            _ACTIVE_RISK,
            RiskAssessment.RiskLevel.in_(("High", "Critical")),
        )
        .order_by(RiskAssessment.RiskScore.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).mappings().all())
