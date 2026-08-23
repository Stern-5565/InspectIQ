from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.role import Role

# Pure many-to-many join, no extra columns beyond the two FKs - a plain Table rather than a
# mapped class, per SQLAlchemy convention for association tables without their own data.
user_roles = Table(
    "UserRoles",
    Base.metadata,
    Column("UserId", Integer, ForeignKey("Users.UserId"), primary_key=True),
    Column("RoleId", Integer, ForeignKey("Roles.RoleId"), primary_key=True),
)


class User(Base):
    __tablename__ = "Users"

    UserId: Mapped[int] = mapped_column(Integer, primary_key=True)
    CompanyId: Mapped[int] = mapped_column(Integer, ForeignKey("Companies.CompanyId"), nullable=False)
    FirstName: Mapped[str] = mapped_column(String(100), nullable=False)
    LastName: Mapped[str] = mapped_column(String(100), nullable=False)
    Email: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    Phone: Mapped[str | None] = mapped_column(String(30))
    PasswordHash: Mapped[str] = mapped_column(String(500), nullable=False)
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("SYSUTCDATETIME()"))
    LastLoginAt: Mapped[datetime | None] = mapped_column(DateTime)

    company: Mapped["Company"] = relationship(back_populates="users")
    roles: Mapped[list["Role"]] = relationship(secondary=user_roles)
