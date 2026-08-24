"""DB access only - no business rules.

MaintenanceIssues carries its own denormalized CompanyId (docs/DATABASE.md §9.5), so get/list
filter directly on it - same pattern as media_file_repository.py, not a join through Properties.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.maintenance_issue import MaintenanceIssue
from app.models.maintenance_update import MaintenanceUpdate


def create_issue(db: Session, issue: MaintenanceIssue) -> MaintenanceIssue:
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


def get_issue_by_id(db: Session, company_id: int, issue_id: int) -> MaintenanceIssue | None:
    stmt = select(MaintenanceIssue).where(
        MaintenanceIssue.CompanyId == company_id, MaintenanceIssue.MaintenanceIssueId == issue_id
    )
    return db.execute(stmt).scalar_one_or_none()


def list_issues(
    db: Session,
    company_id: int,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    property_id: int | None = None,
    assigned_user_id: int | None = None,
) -> tuple[list[MaintenanceIssue], int]:
    stmt = select(MaintenanceIssue).where(MaintenanceIssue.CompanyId == company_id)

    if status is not None:
        stmt = stmt.where(MaintenanceIssue.Status == status)
    if category is not None:
        stmt = stmt.where(MaintenanceIssue.Category == category)
    if priority is not None:
        stmt = stmt.where(MaintenanceIssue.Priority == priority)
    if property_id is not None:
        stmt = stmt.where(MaintenanceIssue.PropertyId == property_id)
    if assigned_user_id is not None:
        stmt = stmt.where(MaintenanceIssue.AssignedUserId == assigned_user_id)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    stmt = (
        stmt.order_by(MaintenanceIssue.ReportedDate.desc(), MaintenanceIssue.MaintenanceIssueId.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.execute(stmt).scalars().all())

    return items, total


def save_issue(db: Session, issue: MaintenanceIssue) -> MaintenanceIssue:
    db.commit()
    db.refresh(issue)
    return issue


def create_update(db: Session, update: MaintenanceUpdate) -> MaintenanceUpdate:
    db.add(update)
    db.commit()
    db.refresh(update)
    return update


def list_updates_for_issue(db: Session, issue_id: int) -> list[MaintenanceUpdate]:
    stmt = (
        select(MaintenanceUpdate)
        .where(MaintenanceUpdate.MaintenanceIssueId == issue_id)
        .order_by(MaintenanceUpdate.MaintenanceUpdateId)
    )
    return list(db.execute(stmt).scalars().all())
