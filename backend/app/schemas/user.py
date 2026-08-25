from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, EmailStr, Field

if TYPE_CHECKING:
    from app.models.user import User


class UserResponse(BaseModel):
    """Public-safe user shape - PasswordHash never appears here or anywhere else outside the
    User model and the auth service."""

    model_config = ConfigDict(from_attributes=True)

    UserId: int
    CompanyId: int
    FirstName: str
    LastName: str
    Email: str
    Phone: str | None
    IsActive: bool
    CreatedAt: datetime
    LastLoginAt: datetime | None
    Roles: list[str]

    @classmethod
    def from_user(cls, user: "User") -> "UserResponse":
        return cls(
            UserId=user.UserId,
            CompanyId=user.CompanyId,
            FirstName=user.FirstName,
            LastName=user.LastName,
            Email=user.Email,
            Phone=user.Phone,
            IsActive=user.IsActive,
            CreatedAt=user.CreatedAt,
            LastLoginAt=user.LastLoginAt,
            Roles=[role.RoleName for role in user.roles],
        )


class UserCreate(BaseModel):
    """Admin Settings' own addition (this module's own docstring named it as the still-unbuilt
    caller). No email-invite flow exists anywhere in this project (no SMTP/notification service
    at all yet - scope §14's "Channels eventually: In-app, Email" is explicitly deferred) - an
    Administrator sets the initial password directly, the practical option available today,
    rather than inventing an invite-email pipeline this pass doesn't need. RoleName is a single
    string, not a list, even though Users/Roles is a real M:N join at the DB level - every
    seeded user in this project has exactly one role (scripts/seed_demo_users.py), and nothing
    in scope or the UI anywhere assumes/needs multi-role support, so the create/edit forms don't
    build UI for a capability nothing exercises."""

    FirstName: str = Field(min_length=1, max_length=100)
    LastName: str = Field(min_length=1, max_length=100)
    Email: EmailStr
    Phone: str | None = Field(default=None, max_length=30)
    Password: str = Field(min_length=8)
    RoleName: str


class UserUpdate(BaseModel):
    """PATCH semantics. Deliberately excludes Email (this project's login identity, unique
    company-wide - scope names no "change my email" requirement, and re-validating uniqueness
    plus the knock-on effect on an already-issued JWT's `sub` claim isn't something this pass
    needs to solve) and Password (a self-service/admin password RESET is a genuinely different,
    security-sensitive feature - not needed to satisfy "inviting/deactivating a user," the job
    this module was built for)."""

    FirstName: str | None = Field(default=None, min_length=1, max_length=100)
    LastName: str | None = Field(default=None, min_length=1, max_length=100)
    Phone: str | None = Field(default=None, max_length=30)
    RoleName: str | None = None
    IsActive: bool | None = None
