"""
Generic polymorphic media endpoints (Phase 9, scope §20) rather than nesting under each parent
module (e.g. NOT /api/properties/{id}/media) - the same EntityType/EntityId a photo is attached
to at the DB level is what the client sends here too, and one router covers every currently
supported entity type instead of duplicating four near-identical route sets. Permission for
every operation is resolved per-request in app/services/media_service.py, not by anything in
the URL - see that module's docstring for the full view/mutate authorization story.
"""
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.database.session import get_db
from app.models.user import User
from app.schemas.media_file import MediaFileResponse, MediaFileUpdate
from app.schemas.pagination import PaginatedResponse
from app.security.dependencies import get_current_user
from app.services import media_service

router = APIRouter(prefix="/media", tags=["media"])

_CHUNK_SIZE = 64 * 1024


def _iter_and_close(stream):
    """StreamingResponse only iterates its content - it never closes a plain file object handed
    to it, which leaked an open file handle on every download (confirmed for real: a test that
    downloaded then immediately tried to delete the same file failed with a Windows
    PermissionError, the file still locked by the never-closed handle from the prior request)."""
    try:
        while chunk := stream.read(_CHUNK_SIZE):
            yield chunk
    finally:
        stream.close()


@router.post("", response_model=MediaFileResponse, status_code=201)
def upload_media(
    entity_type: str = Form(...),
    entity_id: int = Form(...),
    caption: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MediaFileResponse:
    media_file = media_service.upload_media(
        db,
        current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        file=file,
        caption=caption,
    )
    return MediaFileResponse.model_validate(media_file)


@router.get("", response_model=PaginatedResponse[MediaFileResponse])
def list_media(
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[MediaFileResponse]:
    items, total = media_service.list_media(
        db, current_user, entity_type=entity_type, entity_id=entity_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=[MediaFileResponse.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{media_file_id}", response_model=MediaFileResponse)
def get_media(
    media_file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MediaFileResponse:
    media_file = media_service.get_media(db, current_user, media_file_id)
    return MediaFileResponse.model_validate(media_file)


@router.get("/{media_file_id}/download")
def download_media(
    media_file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    media_file = media_service.get_media(db, current_user, media_file_id)
    stream = media_service.open_media_stream(media_file)
    return StreamingResponse(
        _iter_and_close(stream),
        media_type=media_file.ContentType,
        headers={"Content-Disposition": f'inline; filename="{media_file.OriginalFileName}"'},
    )


@router.patch("/{media_file_id}", response_model=MediaFileResponse)
def update_media(
    media_file_id: int,
    payload: MediaFileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MediaFileResponse:
    media_file = media_service.update_media(db, current_user, media_file_id, payload)
    return MediaFileResponse.model_validate(media_file)


@router.delete("/{media_file_id}", status_code=204)
def delete_media(
    media_file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    media_service.delete_media(db, current_user, media_file_id)
