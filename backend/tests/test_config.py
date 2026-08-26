"""Verifies the JWT-secret-placeholder guard (config.py) actually rejects unsafe config -
this is a security-critical validator, not worth trusting without a real test. Mirrors the
finding PropertyManager's Prompt 27 audit caught the hard way (its default JWT secret was
the public .env.example placeholder with nothing stopping production running on it)."""
import pytest
from pydantic import ValidationError

from app.core.config import PLACEHOLDER_JWT_SECRET, Settings


def test_placeholder_secret_rejected_outside_development() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY=PLACEHOLDER_JWT_SECRET,
            DB_SERVER="test-server",
            DB_NAME="test-db",
        )


def test_short_secret_rejected_outside_development() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="too-short",
            DB_SERVER="test-server",
            DB_NAME="test-db",
        )


def test_placeholder_secret_allowed_in_development() -> None:
    s = Settings(
        APP_ENV="development",
        JWT_SECRET_KEY=PLACEHOLDER_JWT_SECRET,
        DB_SERVER="test-server",
        DB_NAME="test-db",
    )
    assert s.JWT_SECRET_KEY == PLACEHOLDER_JWT_SECRET


def test_real_secret_allowed_outside_development() -> None:
    s = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="a-sufficiently-long-random-secret-value-1234567890",
        DB_SERVER="test-server",
        DB_NAME="test-db",
    )
    assert s.APP_ENV == "production"


def test_cors_origins_list_splits_and_strips() -> None:
    s = Settings(
        DB_SERVER="test-server",
        DB_NAME="test-db",
        CORS_ALLOWED_ORIGINS="http://localhost:5173, http://localhost:3000",
    )
    assert s.cors_origins_list == ["http://localhost:5173", "http://localhost:3000"]


# --- MEDIA_STORAGE_PROVIDER guard (Phase 20) -------------------------------------------------


def test_azure_blob_provider_without_connection_string_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(
            DB_SERVER="test-server",
            DB_NAME="test-db",
            MEDIA_STORAGE_PROVIDER="azure_blob",
            AZURE_STORAGE_CONTAINER_NAME="media",
        )


def test_azure_blob_provider_without_container_name_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(
            DB_SERVER="test-server",
            DB_NAME="test-db",
            MEDIA_STORAGE_PROVIDER="azure_blob",
            AZURE_STORAGE_CONNECTION_STRING="fake-connection-string",
        )


def test_azure_blob_provider_with_both_values_allowed() -> None:
    s = Settings(
        DB_SERVER="test-server",
        DB_NAME="test-db",
        MEDIA_STORAGE_PROVIDER="azure_blob",
        AZURE_STORAGE_CONNECTION_STRING="fake-connection-string",
        AZURE_STORAGE_CONTAINER_NAME="media",
    )
    assert s.MEDIA_STORAGE_PROVIDER == "azure_blob"


def test_local_provider_default_unaffected_by_azure_guard() -> None:
    s = Settings(DB_SERVER="test-server", DB_NAME="test-db")
    assert s.MEDIA_STORAGE_PROVIDER == "local"
