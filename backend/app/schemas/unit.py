from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Aliased on import - see app/schemas/property.py's header comment for why (Python 3.14's
# lazy annotation evaluation shadows a module-level import with a same-named class attribute,
# even a bare annotation like `OccupancyStatus: OccupancyStatus`).
from app.schemas.enums import OccupancyStatus as OccupancyStatusEnum


class UnitCreate(BaseModel):
    UnitNumber: str = Field(min_length=1, max_length=50)
    Floor: str | None = Field(default=None, max_length=30)
    OccupancyStatus: OccupancyStatusEnum = OccupancyStatusEnum.UNKNOWN
    TenantOccupierName: str | None = Field(default=None, max_length=200)
    Notes: str | None = None

    # PropertyId comes from the URL path (/api/properties/{property_id}/units), not the body.


class UnitUpdate(BaseModel):
    UnitNumber: str | None = Field(default=None, min_length=1, max_length=50)
    Floor: str | None = Field(default=None, max_length=30)
    TenantOccupierName: str | None = Field(default=None, max_length=200)
    Notes: str | None = None

    # OccupancyStatus deliberately excluded here - scope Prompt 7 asks for it as its own
    # dedicated action ("Change occupancy status"), not folded into the generic update, so a
    # status change is always an explicit, intentional API call rather than an incidental
    # side effect of a broader PATCH. See UnitOccupancyUpdate below.


class UnitOccupancyUpdate(BaseModel):
    OccupancyStatus: OccupancyStatusEnum


class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    UnitId: int
    PropertyId: int
    UnitNumber: str
    Floor: str | None
    OccupancyStatus: str
    TenantOccupierName: str | None
    Notes: str | None
    IsActive: bool
    CreatedAt: datetime
