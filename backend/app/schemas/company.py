from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    CompanyId: int
    CompanyName: str
    AddressLine1: str | None
    AddressLine2: str | None
    City: str | None
    Postcode: str | None
    Telephone: str | None
    Email: str | None
    IsActive: bool
    CreatedAt: datetime


class CompanyUpdate(BaseModel):
    """PATCH semantics. Deliberately excludes CompanyId/IsActive/CreatedAt (a company doesn't
    deactivate itself from its own settings page - that's a platform-operator action outside
    this app's scope, per PROJECT_PLAN.md's multi-tenant premise) and LogoPath (no file-upload
    flow exists for it - scope §4 names "Logo" but building upload/storage for a single company
    logo isn't part of this pass; the column stays available for a future one)."""

    CompanyName: str | None = Field(default=None, min_length=1, max_length=200)
    AddressLine1: str | None = Field(default=None, max_length=200)
    AddressLine2: str | None = Field(default=None, max_length=200)
    City: str | None = Field(default=None, max_length=100)
    Postcode: str | None = Field(default=None, max_length=20)
    Telephone: str | None = Field(default=None, max_length=30)
    Email: str | None = Field(default=None, max_length=200)
