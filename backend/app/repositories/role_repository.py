"""DB access only - no business rules.

Roles has no CompanyId (it's global, shared config - the 5 seeded role names, per
docs/DATABASE.md/scripts/seed_demo_users.py). Nothing queried it outside the seed script until
now - Admin Settings' user-create/edit forms are the first real caller that needs to resolve a
role NAME (submitted from a select field) back to the row UserRoles actually links to.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import Role


def get_role_by_name(db: Session, role_name: str) -> Role | None:
    return db.execute(select(Role).where(Role.RoleName == role_name)).scalar_one_or_none()
