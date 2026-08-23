"""
DB access only - no business rules (PROJECT_PLAN.md §5).

Neither function here takes a CompanyId parameter, which looks like it breaks the "CompanyId
required on every repository method touching tenant data" rule (docs/DATABASE.md §10.1) -
but that rule protects against cross-company LEAKS when listing/filtering another company's
resources. These two lookups are different in kind: get_user_by_email is how login discovers
which company a user belongs to in the first place (Email is deliberately globally unique,
docs/DATABASE.md §10.2, precisely so this lookup can work without already knowing a company),
and get_user_by_id is exclusively used by get_current_user to reload the AUTHENTICATED user's
own record. Neither returns another company's data to someone who shouldn't see it.

A future "admin looks up a user by ID in their own company" endpoint (not part of Phase 5)
WOULD need CompanyId scoping - don't copy this pattern for that case.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).options(joinedload(User.roles)).where(User.Email == email)
    return db.execute(stmt).unique().scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    stmt = select(User).options(joinedload(User.roles)).where(User.UserId == user_id)
    return db.execute(stmt).unique().scalar_one_or_none()
