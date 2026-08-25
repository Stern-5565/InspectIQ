"""DB access only - no business rules.

A company's own record is looked up by its own CompanyId (current_user.CompanyId) - the
simplest possible isolation case in this project, since there's no "list many companies" or
"another company's record" access pattern here at all: an Admin can only ever view/edit their
own company, never anyone else's (docs/PROJECT_PLAN.md's whole multi-tenant premise)."""
from sqlalchemy.orm import Session

from app.models.company import Company


def get_company_by_id(db: Session, company_id: int) -> Company | None:
    return db.get(Company, company_id)


def save_company(db: Session, company: Company) -> Company:
    db.commit()
    db.refresh(company)
    return company
