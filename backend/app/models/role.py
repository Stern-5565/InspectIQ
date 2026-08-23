from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Role(Base):
    __tablename__ = "Roles"

    RoleId: Mapped[int] = mapped_column(Integer, primary_key=True)
    RoleName: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    Description: Mapped[str | None] = mapped_column(String(500))
