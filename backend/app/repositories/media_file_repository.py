"""DB access only - no business rules.

MediaFiles carries its own (denormalized) CompanyId column, unlike Units/Inspections - so
get/list here filter directly on it rather than joining through a parent entity. This is the
same denormalization-for-direct-isolation-queries pattern flagged in docs/DATABASE.md §10.1 for
MaintenanceIssues/RiskAssessments/etc. The finer-grained "does this user's ROLE let them mutate
this specific parent entity" check (e.g. only the assigned inspector can attach evidence to an
in-progress Inspection) is NOT this file's job - that lives in app/services/media_service.py's
per-entity-type resolvers, reusing the parent modules' own services.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.media_file import MediaFile


def create_media_file(db: Session, media_file: MediaFile) -> MediaFile:
    db.add(media_file)
    db.commit()
    db.refresh(media_file)
    return media_file


def get_media_file_by_id(db: Session, company_id: int, media_file_id: int) -> MediaFile | None:
    stmt = select(MediaFile).where(
        MediaFile.CompanyId == company_id, MediaFile.MediaFileId == media_file_id
    )
    return db.execute(stmt).scalar_one_or_none()


def list_media_files_for_entity(
    db: Session,
    company_id: int,
    entity_type: str,
    entity_id: int,
    *,
    page: int,
    page_size: int,
) -> tuple[list[MediaFile], int]:
    stmt = select(MediaFile).where(
        MediaFile.CompanyId == company_id,
        MediaFile.EntityType == entity_type,
        MediaFile.EntityId == entity_id,
    )

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    stmt = stmt.order_by(MediaFile.UploadedAt.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.execute(stmt).scalars().all())

    return items, total


def save_media_file(db: Session, media_file: MediaFile) -> MediaFile:
    db.commit()
    db.refresh(media_file)
    return media_file


def delete_media_file(db: Session, media_file: MediaFile) -> None:
    db.delete(media_file)
    db.commit()
