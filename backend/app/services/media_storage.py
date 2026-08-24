"""Storage abstraction for uploaded media (PROJECT_PLAN.md §8). Local filesystem now; a
production blob-storage implementation (Azure Blob Storage, matching PropertyManager's existing
Azure footprint) is deferred to Phase 20 deployment planning - nothing in media_service.py or
the API layer depends on which implementation is behind IMediaStorageService, only on this
Protocol.

Refinement over the original §8 sketch: `open_stream` was added alongside `save`/`get_url`/
`delete`. The original sketch didn't need it because `get_url` was written assuming a
browser-redirectable URL (true once blob storage exists - a signed URL handed out only after
our own permission check passes, not a substitute for one). Local dev has no such URL scheme:
there's no static file server exposing backend/uploads/ (deliberately - that would bypass the
"authorization mirrors the parent entity" rule in §8 entirely), so the download endpoint needs
to read bytes back through the already-authenticated API instead. `get_url` is kept on the
Protocol for the future blob implementation and returns None for local storage.
"""
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO, Protocol

from fastapi import UploadFile

from app.core.config import settings


class IMediaStorageService(Protocol):
    def save(self, file: UploadFile, entity_type: str, entity_id: int) -> str:
        """Persists the file and returns its storage key."""
        ...

    def open_stream(self, storage_key: str) -> BinaryIO:
        """Returns a readable binary stream for the stored file."""
        ...

    def get_url(self, storage_key: str) -> str | None:
        """A browser-fetchable URL, if the implementation has one (local storage: None)."""
        ...

    def delete(self, storage_key: str) -> None: ...


class LocalFileStorageService:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base_dir = Path(base_dir if base_dir is not None else settings.MEDIA_UPLOAD_DIR)

    def save(self, file: UploadFile, entity_type: str, entity_id: int) -> str:
        extension = Path(file.filename or "").suffix
        storage_key = f"{entity_type}/{entity_id}/{uuid.uuid4().hex}{extension}"
        destination = self._base_dir / storage_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        return storage_key

    def open_stream(self, storage_key: str) -> BinaryIO:
        return (self._base_dir / storage_key).open("rb")

    def get_url(self, storage_key: str) -> str | None:
        return None

    def delete(self, storage_key: str) -> None:
        (self._base_dir / storage_key).unlink(missing_ok=True)


def get_storage_service() -> IMediaStorageService:
    return LocalFileStorageService()
