from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MediaFile(Base):
    __tablename__ = "MediaFiles"

    MediaFileId: Mapped[int] = mapped_column(Integer, primary_key=True)
    CompanyId: Mapped[int] = mapped_column(Integer, ForeignKey("Companies.CompanyId"), nullable=False)
    FileName: Mapped[str] = mapped_column(String(260), nullable=False)
    OriginalFileName: Mapped[str] = mapped_column(String(260), nullable=False)
    ContentType: Mapped[str] = mapped_column(String(100), nullable=False)
    FileSizeBytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    StorageKey: Mapped[str] = mapped_column(String(500), nullable=False)
    # Polymorphic (EntityType, EntityId) - no DB-enforced FK on EntityId, validated at the
    # service layer instead (docs/DATABASE.md §7/§9 - deliberate, see
    # database/tables/07_MediaAndNotesTables.sql's header comment).
    EntityType: Mapped[str] = mapped_column(String(50), nullable=False)
    EntityId: Mapped[int] = mapped_column(Integer, nullable=False)
    Caption: Mapped[str | None] = mapped_column(String(500))
    UploadedByUserId: Mapped[int] = mapped_column(Integer, ForeignKey("Users.UserId"), nullable=False)
    UploadedAt: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
