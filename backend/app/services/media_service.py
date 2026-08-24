"""Media upload/retrieve/delete (Phase 9, scope §20). See app/services/media_storage.py for the
storage abstraction and PROJECT_PLAN.md §8 for the architecture this implements.

SUPPORTED_ENTITY_TYPES is deliberately narrower than scope §20's full list (which also names
MeterReading, RiskAssessment, CleaningInspection). Those tables exist in the DB (Phase 2), but
their own modules/services don't exist yet (Phases 11/13/14) - and §8's core rule is "file
access authorization mirrors the parent entity's authorization," which is impossible to enforce
for a parent entity with no service to ask. Add each one to _VIEW_CHECKS/_MUTATE_CHECKS (and
this tuple) as its own phase lands, the same incremental pattern Phase 7's read-only Templates
API and Phase 8's engine already followed. MaintenanceIssue was added in Phase 10 the same way.

Two authorization levels per entity type, not one:
- View (list/download): can the user see the PARENT entity at all? Reuses each parent module's
  own "get" - Property/Unit/Inspection view is already "any authenticated company member," so
  that's what governs seeing a photo on one too.
- Mutate (upload/implicitly gates delete's "any Admin/Manager" branch): can the user CHANGE the
  parent entity's state? For Property/Unit this is deliberately the SAME as view, not the
  narrower Administrator/Manager-only bar those modules use for editing the property/unit
  record itself - scope explicitly gives the Inspector role "upload evidence" as its own
  standing capability (docs/SCOPE.md - Inspector role), separate from editing a property.
  For Inspection/InspectionResponse it reuses inspection_service.ensure_can_edit (assigned
  inspector or Admin/Manager) - attaching a photo to an in-progress inspection is part of doing
  that inspection, the same "one person's active work" reasoning Phase 8 applied to answers.
"""
from typing import BinaryIO

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.inspection_response import InspectionResponse
from app.models.media_file import MediaFile
from app.models.user import User
from app.repositories import inspection_response_repository as response_repo
from app.repositories import media_file_repository as repo
from app.schemas.media_file import MediaFileUpdate
from app.security import roles
from app.services import inspection_service, property_service, unit_service
from app.services.media_storage import IMediaStorageService, get_storage_service

SUPPORTED_ENTITY_TYPES = ("Property", "Unit", "Inspection", "InspectionResponse", "MaintenanceIssue")

_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
_VIDEO_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
_ALLOWED_CONTENT_TYPES = _IMAGE_CONTENT_TYPES | _VIDEO_CONTENT_TYPES

_MANAGE_ROLES = {roles.ADMINISTRATOR, roles.MANAGER}


def _view_property(db: Session, current_user: User, entity_id: int) -> None:
    property_service.get_property(db, current_user, entity_id)


def _view_unit(db: Session, current_user: User, entity_id: int) -> None:
    unit_service.get_unit(db, current_user, entity_id)


def _view_inspection(db: Session, current_user: User, entity_id: int) -> None:
    inspection_service.get_inspection(db, current_user, entity_id)


def _get_response_for_company(db: Session, current_user: User, entity_id: int) -> InspectionResponse:
    response = response_repo.get_response_by_id_for_company(db, current_user.CompanyId, entity_id)
    if response is None:
        raise NotFoundError("Inspection response not found.")
    return response


def _view_inspection_response(db: Session, current_user: User, entity_id: int) -> None:
    _get_response_for_company(db, current_user, entity_id)


def _mutate_inspection(db: Session, current_user: User, entity_id: int) -> None:
    inspection = inspection_service.get_inspection(db, current_user, entity_id)
    inspection_service.ensure_can_edit(current_user, inspection)


def _mutate_inspection_response(db: Session, current_user: User, entity_id: int) -> None:
    response = _get_response_for_company(db, current_user, entity_id)
    inspection = inspection_service.get_inspection(db, current_user, response.InspectionId)
    inspection_service.ensure_can_edit(current_user, inspection)


def _view_maintenance_issue(db: Session, current_user: User, entity_id: int) -> None:
    # Local import: maintenance_service.upload_photo calls INTO media_service.upload_media,
    # which reaches this function - a top-level import either direction would be circular. See
    # maintenance_service.py's upload_photo for the matching local import on that side.
    from app.services import maintenance_service

    maintenance_service.get_issue(db, current_user, entity_id)


def _mutate_maintenance_issue(db: Session, current_user: User, entity_id: int) -> None:
    from app.services import maintenance_service

    issue = maintenance_service.get_issue(db, current_user, entity_id)
    maintenance_service.ensure_can_edit(current_user, issue)


_VIEW_CHECKS = {
    "Property": _view_property,
    "Unit": _view_unit,
    "Inspection": _view_inspection,
    "InspectionResponse": _view_inspection_response,
    "MaintenanceIssue": _view_maintenance_issue,
}

_MUTATE_CHECKS = {
    "Property": _view_property,
    "Unit": _view_unit,
    "Inspection": _mutate_inspection,
    "InspectionResponse": _mutate_inspection_response,
    "MaintenanceIssue": _mutate_maintenance_issue,
}


def _ensure_supported_entity_type(entity_type: str) -> None:
    if entity_type not in SUPPORTED_ENTITY_TYPES:
        raise ValidationError(
            f"Unsupported EntityType '{entity_type}'. Supported: {', '.join(SUPPORTED_ENTITY_TYPES)}."
        )


def upload_media(
    db: Session,
    current_user: User,
    *,
    entity_type: str,
    entity_id: int,
    file: UploadFile,
    caption: str | None,
    storage: IMediaStorageService | None = None,
) -> MediaFile:
    _ensure_supported_entity_type(entity_type)
    _MUTATE_CHECKS[entity_type](db, current_user, entity_id)  # 404s/403s if not allowed

    content_type = file.content_type or ""
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            f"Unsupported file type '{content_type}'. Allowed: {', '.join(sorted(_ALLOWED_CONTENT_TYPES))}."
        )

    max_size = (
        settings.MEDIA_MAX_VIDEO_SIZE_BYTES
        if content_type in _VIDEO_CONTENT_TYPES
        else settings.MEDIA_MAX_IMAGE_SIZE_BYTES
    )
    # UploadFile doesn't expose a reliable pre-read size; validation is on the byte count
    # actually written to disk. This happens AFTER the mutate-permission check above (fail fast
    # on authorization before spending I/O) but the oversized file is deleted immediately if the
    # limit is exceeded - never left orphaned on disk.
    storage = storage or get_storage_service()
    storage_key = storage.save(file, entity_type, entity_id)
    size_bytes = file.file.tell()
    if size_bytes > max_size:
        storage.delete(storage_key)
        raise ValidationError(
            f"File exceeds the maximum allowed size of {max_size} bytes for this content type."
        )

    media_file = MediaFile(
        CompanyId=current_user.CompanyId,
        FileName=storage_key.rsplit("/", 1)[-1],
        OriginalFileName=file.filename or "upload",
        ContentType=content_type,
        FileSizeBytes=size_bytes,
        StorageKey=storage_key,
        EntityType=entity_type,
        EntityId=entity_id,
        Caption=caption,
        UploadedByUserId=current_user.UserId,
    )
    return repo.create_media_file(db, media_file)


def list_media(
    db: Session,
    current_user: User,
    *,
    entity_type: str,
    entity_id: int,
    page: int,
    page_size: int,
) -> tuple[list[MediaFile], int]:
    _ensure_supported_entity_type(entity_type)
    _VIEW_CHECKS[entity_type](db, current_user, entity_id)  # 404s if the parent isn't visible
    return repo.list_media_files_for_entity(
        db, current_user.CompanyId, entity_type, entity_id, page=page, page_size=page_size
    )


def get_media(db: Session, current_user: User, media_file_id: int) -> MediaFile:
    # MediaFiles carries its own CompanyId (docs/DATABASE.md §7), so this alone already matches
    # the "any company member can view" level every supported entity type's view check grants -
    # no need to re-resolve and re-check the parent entity on every single read.
    media_file = repo.get_media_file_by_id(db, current_user.CompanyId, media_file_id)
    if media_file is None:
        raise NotFoundError("Media file not found.")
    return media_file


def open_media_stream(media_file: MediaFile, storage: IMediaStorageService | None = None) -> BinaryIO:
    storage = storage or get_storage_service()
    return storage.open_stream(media_file.StorageKey)


def _ensure_can_modify(current_user: User, media_file: MediaFile, action: str) -> None:
    """Editing a caption or deleting a file is gated to whoever uploaded it, or an
    Administrator/Manager - not the broader "any company member who can view the parent
    entity" bar that governs upload/list/download. Someone else's evidence shouldn't be
    silently editable/removable just by sharing company membership."""
    is_uploader = current_user.UserId == media_file.UploadedByUserId
    user_role_names = {role.RoleName for role in current_user.roles}
    is_manager_or_admin = bool(user_role_names.intersection(_MANAGE_ROLES))
    if not (is_uploader or is_manager_or_admin):
        raise ForbiddenError(f"Only the uploader, a Manager, or an Administrator can {action} this file.")


def update_media(
    db: Session, current_user: User, media_file_id: int, payload: MediaFileUpdate
) -> MediaFile:
    media_file = get_media(db, current_user, media_file_id)
    _ensure_can_modify(current_user, media_file, "edit")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(media_file, field, value)
    return repo.save_media_file(db, media_file)


def delete_media(
    db: Session, current_user: User, media_file_id: int, storage: IMediaStorageService | None = None
) -> None:
    media_file = get_media(db, current_user, media_file_id)
    _ensure_can_modify(current_user, media_file, "delete")

    storage = storage or get_storage_service()
    storage.delete(media_file.StorageKey)
    repo.delete_media_file(db, media_file)
