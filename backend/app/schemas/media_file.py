from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Kept in sync by hand with app/services/media_service.py's SUPPORTED_ENTITY_TYPES - see that
# module's docstring for why this list is narrower than scope §20's full set for now.
ENTITY_TYPES = (
    "Property",
    "Unit",
    "Inspection",
    "InspectionResponse",
    "MaintenanceIssue",
    "CleaningInspection",
)


class MediaFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    MediaFileId: int
    OriginalFileName: str
    ContentType: str
    FileSizeBytes: int
    EntityType: str
    EntityId: int
    Caption: str | None
    UploadedByUserId: int
    UploadedAt: datetime


class MediaFileUpdate(BaseModel):
    Caption: str | None = Field(default=None, max_length=500)
