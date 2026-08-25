"""Admin Settings' User Management half (scope §3 Module 1), alongside company_service.py.

Both mutating actions (create/update) are Administrator-ONLY - the first Admin-only tier in
this project that excludes Manager. Every prior "narrower than any-company-member" tier still
included Manager alongside Administrator (Properties/Maintenance/Cleaning's general edits, etc.)
- confirmed this one doesn't by rereading scope §3's own role table: Manager's definition
("Manage properties, view all inspections, assign inspections, manage maintenance, view
reports") names nothing about managing teammates, and only Administrator is described as "Full
access." View (list) has no role restriction, unchanged from when app/api/users.py was added
for the Maintenance module's "assign to" picker - any company member can see their colleagues.

RoleName is validated against the real Roles table (role_repository.get_role_by_name), not just
a Python constant list - the DB row is what UserRoles actually links to.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.user import User
from app.repositories import role_repository, user_repository
from app.schemas.user import UserCreate, UserUpdate
from app.security.password import hash_password


def list_users(db: Session, current_user: User, *, include_inactive: bool = False) -> list[User]:
    return user_repository.list_users_for_company(db, current_user.CompanyId, include_inactive=include_inactive)


def get_user(db: Session, current_user: User, user_id: int) -> User:
    user = user_repository.get_user_by_id_for_company(db, current_user.CompanyId, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def create_user(db: Session, current_user: User, payload: UserCreate) -> User:
    if user_repository.get_user_by_email(db, payload.Email) is not None:
        raise ConflictError("A user with this email already exists.")

    role = role_repository.get_role_by_name(db, payload.RoleName)
    if role is None:
        raise ValidationError(f"Unknown role '{payload.RoleName}'.")

    user = User(
        CompanyId=current_user.CompanyId,
        FirstName=payload.FirstName,
        LastName=payload.LastName,
        Email=payload.Email,
        Phone=payload.Phone,
        PasswordHash=hash_password(payload.Password),
    )
    user.roles = [role]
    return user_repository.create_user(db, user)


def update_user(db: Session, current_user: User, user_id: int, payload: UserUpdate) -> User:
    user = get_user(db, current_user, user_id)

    data = payload.model_dump(exclude_unset=True)

    if data.get("IsActive") is False and user.UserId == current_user.UserId:
        raise ValidationError("You cannot deactivate your own account.")

    role_name = data.pop("RoleName", None)
    if role_name is not None:
        role = role_repository.get_role_by_name(db, role_name)
        if role is None:
            raise ValidationError(f"Unknown role '{role_name}'.")
        user.roles = [role]

    for field, value in data.items():
        setattr(user, field, value)
    return user_repository.save_user(db, user)
