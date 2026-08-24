"""Media API tests - same conventions as test_units.py/test_inspections.py (real DB, no mocks,
explicit cleanup - including deleting any file actually written to backend/uploads/)."""
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.inspection import Inspection
from app.models.inspection_response import InspectionResponse
from app.models.inspection_template import InspectionTemplate
from app.models.media_file import MediaFile
from app.models.property import Property
from tests.conftest import auth_headers, delete_user, make_user

# Content validation is by declared Content-Type + size only (docs/PROJECT_PLAN.md §8) - no
# magic-byte sniffing of the body - so an arbitrary small payload is fine for these tests as
# long as it's sent with an allowed Content-Type.
_TINY_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32 + b"\xff\xd9"


@pytest.fixture
def northgate_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.media.admin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.media.inspector.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_inspector2(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Northgate Property Management",
        email="test.media.inspector2.tmp@example.com",
        role_name="Inspector",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def bright_spaces_admin(db_session: Session) -> Generator[dict, None, None]:
    user = make_user(
        db_session,
        company_name="Bright Spaces Estates",
        email="test.media.bsadmin.tmp@example.com",
        role_name="Administrator",
    )
    yield user
    delete_user(db_session, user)


@pytest.fixture
def northgate_property_id(db_session: Session) -> int:
    return db_session.execute(
        select(Property.PropertyId).where(Property.PropertyName == "15 High Road")
    ).scalar_one()


def _delete_media_row(db_session: Session, media_file_id: int) -> None:
    media_file = db_session.get(MediaFile, media_file_id)
    if media_file is None:
        return
    file_path = Path(settings.MEDIA_UPLOAD_DIR) / media_file.StorageKey
    file_path.unlink(missing_ok=True)
    db_session.delete(media_file)
    db_session.commit()


def _upload(client: TestClient, headers: dict, entity_type: str, entity_id: int, **extra) -> "TestClient":
    return client.post(
        "/api/media",
        data={"entity_type": entity_type, "entity_id": entity_id, **extra},
        files={"file": ("test.jpg", _TINY_JPEG, "image/jpeg")},
        headers=headers,
    )


def test_upload_and_download_photo_on_property(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    response = _upload(client, headers, "Property", northgate_property_id, caption="Front entrance")

    try:
        assert response.status_code == 201
        body = response.json()
        assert body["EntityType"] == "Property"
        assert body["EntityId"] == northgate_property_id
        assert body["Caption"] == "Front entrance"
        assert body["ContentType"] == "image/jpeg"
        media_file_id = body["MediaFileId"]

        stored_path = Path(settings.MEDIA_UPLOAD_DIR) / f"Property/{northgate_property_id}"
        assert any(stored_path.iterdir())

        download = client.get(f"/api/media/{media_file_id}/download", headers=headers)
        assert download.status_code == 200
        assert download.content == _TINY_JPEG
        assert download.headers["content-type"] == "image/jpeg"

        listing = client.get(
            "/api/media",
            params={"entity_type": "Property", "entity_id": northgate_property_id},
            headers=headers,
        )
        assert listing.status_code == 200
        assert listing.json()["total"] == 1
    finally:
        _delete_media_row(db_session, response.json()["MediaFileId"])


def test_upload_for_property_in_another_company_returns_404(
    client: TestClient, bright_spaces_admin, northgate_property_id: int
) -> None:
    response = _upload(client, auth_headers(client, bright_spaces_admin.Email), "Property", northgate_property_id)
    assert response.status_code == 404


def test_upload_with_unsupported_entity_type_returns_422(
    client: TestClient, northgate_inspector, northgate_property_id: int
) -> None:
    # RiskAssessment's own service doesn't exist yet (Phase 13) - still a genuinely unsupported
    # EntityType. MaintenanceIssue stopped being a valid example of this the moment Phase 10
    # added it to media_service.SUPPORTED_ENTITY_TYPES.
    response = _upload(client, auth_headers(client, northgate_inspector.Email), "RiskAssessment", 1)
    assert response.status_code == 422


def test_upload_with_unsupported_content_type_returns_422(
    client: TestClient, northgate_inspector, northgate_property_id: int
) -> None:
    response = client.post(
        "/api/media",
        data={"entity_type": "Property", "entity_id": northgate_property_id},
        files={"file": ("notes.txt", b"plain text", "text/plain")},
        headers=auth_headers(client, northgate_inspector.Email),
    )
    assert response.status_code == 422


def test_delete_by_uploader_removes_row_and_file(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    upload = _upload(client, headers, "Property", northgate_property_id)
    media_file_id = upload.json()["MediaFileId"]
    storage_key = db_session.get(MediaFile, media_file_id).StorageKey
    file_path = Path(settings.MEDIA_UPLOAD_DIR) / storage_key

    response = client.delete(f"/api/media/{media_file_id}", headers=headers)
    assert response.status_code == 204

    db_session.expire_all()
    assert db_session.get(MediaFile, media_file_id) is None
    assert not file_path.exists()


def test_delete_by_non_uploader_non_admin_returns_403(
    client: TestClient, db_session: Session, northgate_inspector, northgate_inspector2, northgate_property_id: int
) -> None:
    upload = _upload(client, auth_headers(client, northgate_inspector.Email), "Property", northgate_property_id)
    media_file_id = upload.json()["MediaFileId"]

    try:
        response = client.delete(
            f"/api/media/{media_file_id}", headers=auth_headers(client, northgate_inspector2.Email)
        )
        assert response.status_code == 403
    finally:
        _delete_media_row(db_session, media_file_id)


def test_upload_to_inspection_by_unassigned_inspector_returns_403(
    client: TestClient,
    db_session: Session,
    northgate_inspector,
    northgate_inspector2,
    northgate_property_id: int,
) -> None:
    template_id = db_session.execute(
        select(InspectionTemplate.InspectionTemplateId).where(
            InspectionTemplate.TemplateName == "Monthly Property Inspection"
        )
    ).scalar_one()
    start = client.post(
        "/api/inspections",
        json={"PropertyId": northgate_property_id, "InspectionTemplateId": template_id},
        headers=auth_headers(client, northgate_inspector.Email),
    )
    inspection_id = start.json()["InspectionId"]

    try:
        response = _upload(
            client, auth_headers(client, northgate_inspector2.Email), "Inspection", inspection_id
        )
        assert response.status_code == 403
    finally:
        db_session.query(InspectionResponse).filter(InspectionResponse.InspectionId == inspection_id).delete()
        db_session.query(Inspection).filter(Inspection.InspectionId == inspection_id).delete()
        db_session.commit()


def test_update_caption_by_uploader(
    client: TestClient, db_session: Session, northgate_inspector, northgate_property_id: int
) -> None:
    headers = auth_headers(client, northgate_inspector.Email)
    upload = _upload(client, headers, "Property", northgate_property_id, caption="Original")
    media_file_id = upload.json()["MediaFileId"]

    try:
        response = client.patch(
            f"/api/media/{media_file_id}", json={"Caption": "Updated caption"}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["Caption"] == "Updated caption"
    finally:
        _delete_media_row(db_session, media_file_id)
