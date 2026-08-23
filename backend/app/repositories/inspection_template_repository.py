"""DB access only - no business rules.

CompanyId filtering here is the "global default + per-company override" pattern
(docs/DATABASE.md §9.3), not the plain single-company filter used elsewhere: a template is
visible if it's global (CompanyId IS NULL) OR belongs to the caller's own company. A
company-specific template belonging to a DIFFERENT company matches neither condition, so it's
excluded automatically - the same 404-not-403 isolation outcome as Properties/Units, achieved
here by the WHERE clause itself rather than a separate check.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.inspection_section import InspectionSection
from app.models.inspection_template import InspectionTemplate


def _visible_to_company(company_id: int):
    return (InspectionTemplate.CompanyId == company_id) | (InspectionTemplate.CompanyId.is_(None))


def list_templates(db: Session, company_id: int, *, include_inactive: bool = False) -> list[InspectionTemplate]:
    stmt = select(InspectionTemplate).where(_visible_to_company(company_id))
    if not include_inactive:
        stmt = stmt.where(InspectionTemplate.IsActive == True)  # noqa: E712
    stmt = stmt.order_by(InspectionTemplate.TemplateName)
    return list(db.execute(stmt).scalars().all())


def get_template_by_id(db: Session, company_id: int, template_id: int) -> InspectionTemplate | None:
    stmt = (
        select(InspectionTemplate)
        .where(
            InspectionTemplate.InspectionTemplateId == template_id,
            _visible_to_company(company_id),
        )
        .options(joinedload(InspectionTemplate.sections).joinedload(InspectionSection.questions))
    )
    return db.execute(stmt).unique().scalar_one_or_none()
