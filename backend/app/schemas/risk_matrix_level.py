from pydantic import BaseModel, ConfigDict, Field


class RiskMatrixLevelCreate(BaseModel):
    MinScore: int = Field(ge=1, le=25)
    MaxScore: int = Field(ge=1, le=25)
    LevelName: str = Field(min_length=1, max_length=20)
    SortOrder: int = 0
    ColorHint: str | None = Field(default=None, max_length=20)

    # CompanyId comes from the authenticated user, never the client (app/services/
    # risk_service.py) - creating one here always creates/adds to THIS company's own override
    # matrix, never a global-default row (those are seeded once, company-less, and read-only
    # through this API).


class RiskMatrixLevelUpdate(BaseModel):
    MinScore: int | None = Field(default=None, ge=1, le=25)
    MaxScore: int | None = Field(default=None, ge=1, le=25)
    LevelName: str | None = Field(default=None, min_length=1, max_length=20)
    SortOrder: int | None = None
    ColorHint: str | None = Field(default=None, max_length=20)


class RiskMatrixLevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    RiskMatrixLevelId: int
    CompanyId: int | None
    MinScore: int
    MaxScore: int
    LevelName: str
    SortOrder: int
    ColorHint: str | None
