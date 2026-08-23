from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

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
