"""
One-off script to seed demo login accounts using the app's own password hashing.

The SQL seed scripts under database/seed/ deliberately don't do this themselves - SQL Server
has no bcrypt function, and a fake/placeholder hash would create rows that look like working
logins but aren't (see database/seed/13_SeedSampleData.sql's header comment). Now that Phase 5
(Authentication) exists and can hash a real password correctly, this closes that gap.

Local dev only - mirrors PropertyManager's one-off pyodbc script for creating its real
Administrator account, but for throwaway demo credentials, not a production login. Never run
against production; a real deployment creates its actual Administrator account the same way
PropertyManager did (a one-off script using this same hash_password function, real credentials
saved outside the repo).

Run from backend/ with the venv active:

    python -m scripts.seed_demo_users

Idempotent - skips any email that already exists.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.company import Company
from app.models.role import Role
from app.models.user import User, user_roles
from app.security.password import hash_password

DEMO_PASSWORD = "Password123!"

# One user per role, same convention PropertyManager used for its demo accounts.
NORTHGATE_USERS = [
    ("Alice", "Admin", "admin@northgatepm.example", "Administrator"),
    ("Mo", "Manager", "manager@northgatepm.example", "Manager"),
    ("Ivy", "Inspector", "inspector@northgatepm.example", "Inspector"),
    ("Max", "Maintenance", "maintenance@northgatepm.example", "Maintenance"),
    ("Val", "Viewer", "viewer@northgatepm.example", "Viewer"),
]

# Deliberately minimal - exists so cross-company isolation testing (Phase 19) has a second
# company's real user to test against, not to exercise every role again.
BRIGHT_SPACES_USERS = [
    ("Bea", "Admin", "admin@brightspaces.example", "Administrator"),
]


def seed_company_users(db: Session, company_name: str, users: list[tuple[str, str, str, str]]) -> None:
    company = db.execute(select(Company).where(Company.CompanyName == company_name)).scalar_one()

    for first_name, last_name, email, role_name in users:
        existing = db.execute(select(User).where(User.Email == email)).scalar_one_or_none()
        if existing is not None:
            print(f"  {email} already exists - skipping.")
            continue

        role = db.execute(select(Role).where(Role.RoleName == role_name)).scalar_one()
        user = User(
            CompanyId=company.CompanyId,
            FirstName=first_name,
            LastName=last_name,
            Email=email,
            PasswordHash=hash_password(DEMO_PASSWORD),
            IsActive=True,
        )
        db.add(user)
        db.flush()
        db.execute(user_roles.insert().values(UserId=user.UserId, RoleId=role.RoleId))
        print(f"  Created {email} ({role_name}).")


def main() -> None:
    db = SessionLocal()
    try:
        print(f"Demo password for every account below: {DEMO_PASSWORD}\n")
        print("Northgate Property Management:")
        seed_company_users(db, "Northgate Property Management", NORTHGATE_USERS)
        print("Bright Spaces Estates:")
        seed_company_users(db, "Bright Spaces Estates", BRIGHT_SPACES_USERS)
        db.commit()
        print("\nDone.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
