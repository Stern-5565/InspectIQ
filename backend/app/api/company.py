"""
Admin Settings' Company Profile half (see app/services/company_service.py's module docstring).
View is open to any authenticated company user; update is Administrator-only, gated at the
ROUTE level via require_roles (a static role gate is sufficient - unlike Inspections/Maintenance,
there's no per-record assignee carve-out possible for "your own company's profile").

Deliberately no path parameter (no `/company/{id}`) - a user can only ever see/edit their OWN
company, resolved from current_user.CompanyId, never an arbitrary one (the multi-tenant
isolation premise this whole project is built on, docs/PROJECT_PLAN.md).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.company import CompanyResponse, CompanyUpdate
from app.security import roles
from app.security.dependencies import get_current_user, require_roles
from app.services import company_service

router = APIRouter(prefix="/company", tags=["company"])

_manage_company = require_roles(roles.ADMINISTRATOR)


@router.get("", response_model=CompanyResponse)
def get_company(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyResponse:
    company = company_service.get_company(db, current_user)
    return CompanyResponse.model_validate(company)


@router.patch("", response_model=CompanyResponse)
def update_company(
    payload: CompanyUpdate,
    current_user: User = Depends(_manage_company),
    db: Session = Depends(get_db),
) -> CompanyResponse:
    company = company_service.update_company(db, current_user, payload)
    return CompanyResponse.model_validate(company)
