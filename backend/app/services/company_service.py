"""Company Profile (scope §4), the second half of Admin Settings alongside user_service.py.

View: any company member (a company's own name/address/contact details aren't sensitive the
way user accounts are - matches every other module's view side). Update: Administrator only -
the same narrower-than-Admin/Manager tier user_service.py establishes, since a company's own
identity/contact details are a full-access-only concern per scope §3's role table ("Administrator
- Full access", no other role named for company-level settings).
"""
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.company import Company
from app.models.user import User
from app.repositories import company_repository as repo
from app.schemas.company import CompanyUpdate


def get_company(db: Session, current_user: User) -> Company:
    company = repo.get_company_by_id(db, current_user.CompanyId)
    if company is None:
        raise NotFoundError("Company not found.")
    return company


def update_company(db: Session, current_user: User, payload: CompanyUpdate) -> Company:
    company = get_company(db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    return repo.save_company(db, company)
