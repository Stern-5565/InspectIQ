"""DB access only - no business rules.

RiskAssessments carries its own denormalized CompanyId (docs/DATABASE.md §9.5), same pattern as
MaintenanceIssues/MediaFiles - get/list filter directly on it. RiskMatrixLevels has a nullable
CompanyId (NULL = global default) but no isolation concerns of its own to speak of: reading a
company's risk matrix never needs to hide it from other companies (it isn't tenant-sensitive
data), so get_risk_matrix_for_company takes no isolation-checked "get single row" counterpart -
callers always work with the resolved list.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.risk_assessment import RiskAssessment
from app.models.risk_matrix_level import RiskMatrixLevel


def create_risk_assessment(db: Session, risk_assessment: RiskAssessment) -> RiskAssessment:
    db.add(risk_assessment)
    db.commit()
    db.refresh(risk_assessment)
    return risk_assessment


def get_risk_assessment_by_id(db: Session, company_id: int, risk_assessment_id: int) -> RiskAssessment | None:
    stmt = select(RiskAssessment).where(
        RiskAssessment.CompanyId == company_id, RiskAssessment.RiskAssessmentId == risk_assessment_id
    )
    return db.execute(stmt).scalar_one_or_none()


def list_risk_assessments(
    db: Session,
    company_id: int,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    risk_level: str | None = None,
    property_id: int | None = None,
) -> tuple[list[RiskAssessment], int]:
    stmt = select(RiskAssessment).where(RiskAssessment.CompanyId == company_id)
    if status is not None:
        stmt = stmt.where(RiskAssessment.Status == status)
    if risk_level is not None:
        stmt = stmt.where(RiskAssessment.RiskLevel == risk_level)
    if property_id is not None:
        stmt = stmt.where(RiskAssessment.PropertyId == property_id)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    stmt = (
        stmt.order_by(RiskAssessment.RiskScore.desc(), RiskAssessment.RiskAssessmentId.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.execute(stmt).scalars().all())

    return items, total


def save_risk_assessment(db: Session, risk_assessment: RiskAssessment) -> RiskAssessment:
    db.commit()
    db.refresh(risk_assessment)
    return risk_assessment


def create_risk_matrix_level(db: Session, level: RiskMatrixLevel) -> RiskMatrixLevel:
    db.add(level)
    db.commit()
    db.refresh(level)
    return level


def get_risk_matrix_level_by_id(
    db: Session, company_id: int, risk_matrix_level_id: int
) -> RiskMatrixLevel | None:
    # Deliberately scoped to THIS company's own rows only (never CompanyId IS NULL) - global
    # default levels are read-only through the API, not editable by any company.
    stmt = select(RiskMatrixLevel).where(
        RiskMatrixLevel.CompanyId == company_id, RiskMatrixLevel.RiskMatrixLevelId == risk_matrix_level_id
    )
    return db.execute(stmt).scalar_one_or_none()


def get_risk_matrix_for_company(db: Session, company_id: int) -> list[RiskMatrixLevel]:
    """A company's own bands fully REPLACE the global default the moment any exist - not an
    additive list. Mixing, say, two company-specific bands with two leftover global ones could
    easily leave score gaps or overlaps a coherent matrix must not have."""
    company_levels = list(
        db.execute(
            select(RiskMatrixLevel)
            .where(RiskMatrixLevel.CompanyId == company_id)
            .order_by(RiskMatrixLevel.SortOrder)
        ).scalars().all()
    )
    if company_levels:
        return company_levels

    return list(
        db.execute(
            select(RiskMatrixLevel).where(RiskMatrixLevel.CompanyId.is_(None)).order_by(RiskMatrixLevel.SortOrder)
        ).scalars().all()
    )


def save_risk_matrix_level(db: Session, level: RiskMatrixLevel) -> RiskMatrixLevel:
    db.commit()
    db.refresh(level)
    return level
