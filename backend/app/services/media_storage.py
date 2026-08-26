"""Storage abstraction for uploaded media (PROJECT_PLAN.md §8). Local filesystem for dev;
Azure Blob Storage for production (Phase 20) - nothing in media_service.py or the API layer
depends on which implementation is behind IMediaStorageService, only on this Protocol.

Refinement over the original §8 sketch: `open_stream` was added alongside `save`/`get_url`/
`delete`. The original sketch didn't need it because `get_url` was written assuming a
browser-redirectable URL. Deliberately NOT used that way even now that blob storage exists:
`get_url` still returns None from BOTH implementations, on purpose - a signed/anonymous blob
URL would let a client bypass this app's own per-request permission check (the exact thing the
original §8 sketch's "authorization mirrors the parent entity" rule was written to prevent), so
`download_media` (app/api/media.py) always proxies bytes back through the already-authenticated
API instead. `get_url` is kept on the Protocol only in case a genuinely public-content use case
ever needs it later - it isn't dead code by oversight, it's a deliberately unused escape hatch.
"""
import io
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


class AzureBlobStorageService:
    """Production implementation. Container access level must stay Private (never Blob/
    Container anonymous read) - `get_url` returning None is enforced by convention everywhere
    else, but a publicly-readable container would bypass it at the Azure layer regardless, so
    this is a deployment-time setting to get right once, not something this class can guard.

    Lazily creates the Azure SDK client in __init__ rather than at import time, so importing
    this module (e.g. for the Protocol/LocalFileStorageService in tests) never requires
    `azure-storage-blob` to be installed or a connection string to be configured - only
    actually instantiating this class does.
    """

    def __init__(self, connection_string: str | None = None, container_name: str | None = None) -> None:
        from azure.storage.blob import BlobServiceClient

        connection_string = connection_string or settings.AZURE_STORAGE_CONNECTION_STRING
        container_name = container_name or settings.AZURE_STORAGE_CONTAINER_NAME
        if not connection_string or not container_name:
            raise ValueError(
                "AZURE_STORAGE_CONNECTION_STRING and AZURE_STORAGE_CONTAINER_NAME must both be "
                "set to use AzureBlobStorageService."
            )
        self._container = BlobServiceClient.from_connection_string(
            connection_string
        ).get_container_client(container_name)

    def save(self, file: UploadFile, entity_type: str, entity_id: int) -> str:
        # Same storage_key SHAPE as LocalFileStorageService ("entity_type/entity_id/uuid.ext")
        # deliberately - MediaFiles.StorageKey (app/models/media_file.py) has no format
        # assumptions baked into it anywhere else, so keeping this identical means an existing
        # local-storage-era row would even resolve correctly if the same key were ever copied
        # into blob storage, not just that new rows work.
        extension = Path(file.filename or "").suffix
        storage_key = f"{entity_type}/{entity_id}/{uuid.uuid4().hex}{extension}"
        self._container.upload_blob(name=storage_key, data=file.file, overwrite=False)
        return storage_key

    def open_stream(self, storage_key: str) -> BinaryIO:
        # Buffered fully into memory rather than streamed chunk-by-chunk - StorageStreamDownloader
        # isn't a drop-in BinaryIO (no matching read(size)/close() pair app/api/media.py's
        # _iter_and_close generator needs), and at this project's real size ceiling
        # (MEDIA_MAX_VIDEO_SIZE_BYTES = 250MB, docs/DATABASE.md's own documented limit) that's
        # an acceptable simplification for a project this size, not a hidden landmine - revisit
        # with a real chunked wrapper if this ever needs to serve high concurrent video traffic.
        downloader = self._container.download_blob(storage_key)
        return io.BytesIO(downloader.readall())

    def get_url(self, storage_key: str) -> str | None:
        return None

    def delete(self, storage_key: str) -> None:
        self._container.delete_blob(storage_key, delete_snapshots="include")


def get_storage_service() -> IMediaStorageService:
    if settings.MEDIA_STORAGE_PROVIDER == "azure_blob":
        return AzureBlobStorageService()
    return LocalFileStorageService()
