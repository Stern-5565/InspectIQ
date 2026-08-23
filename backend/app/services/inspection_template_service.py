from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.inspection_template import InspectionTemplate
from app.models.user import User
from app.repositories import inspection_template_repository as repo


def list_templates(
    db: Session, current_user: User, *, include_inactive: bool = False
) -> list[InspectionTemplate]:
    return repo.list_templates(db, current_user.CompanyId, include_inactive=include_inactive)


def get_template(db: Session, current_user: User, template_id: int) -> InspectionTemplate:
    template = repo.get_template_by_id(db, current_user.CompanyId, template_id)
    if template is None:
        # 404, not 403 - same isolation principle as Properties/Units (docs/DATABASE.md §10.1):
        # a company-specific template belonging to another company must look identical to one
        # that doesn't exist.
        raise NotFoundError("Inspection template not found.")
    return template
