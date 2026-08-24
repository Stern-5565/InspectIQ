"""
Two authorization tiers - see app/services/risk_service.py's module docstring for the full
reasoning. RiskAssessments: view = any company member; create = Administrator/Manager/Inspector
(raising a hazard, same tier Maintenance's create uses); update = Administrator/Manager only,
covering every field (including Status) in one PATCH - no assigned-inspector carve-out, since a
standalone assessment may have no parent Inspection to check at all. RiskMatrixLevels: view =
any company member; create/update = Administrator/Manager only, the same "per-company
configuration" shape CleaningAreas uses.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.risk_assessment import (
    RiskAssessmentCreate,
    RiskAssessmentResponse,
    RiskAssessmentUpdate,
)
from app.schemas.risk_matrix_level import (
    RiskMatrixLevelCreate,
    RiskMatrixLevelResponse,
    RiskMatrixLevelUpdate,
)
from app.security import roles
from app.security.dependencies import get_current_user, require_roles
from app.services import risk_service

router = APIRouter(tags=["risk"])

_raise_risks = require_roles(roles.ADMINISTRATOR, roles.MANAGER, roles.INSPECTOR)
_manage_risks = require_roles(roles.ADMINISTRATOR, roles.MANAGER)


@router.get("/risk-matrix-levels", response_model=list[RiskMatrixLevelResponse])
def get_risk_matrix(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RiskMatrixLevelResponse]:
    levels = risk_service.get_risk_matrix(db, current_user)
    return [RiskMatrixLevelResponse.model_validate(level) for level in levels]


@router.post("/risk-matrix-levels", response_model=RiskMatrixLevelResponse, status_code=201)
def create_risk_matrix_level(
    payload: RiskMatrixLevelCreate,
    current_user: User = Depends(_manage_risks),
    db: Session = Depends(get_db),
) -> RiskMatrixLevelResponse:
    level = risk_service.create_risk_matrix_level(db, current_user, payload)
    return RiskMatrixLevelResponse.model_validate(level)


@router.patch("/risk-matrix-levels/{risk_matrix_level_id}", response_model=RiskMatrixLevelResponse)
def update_risk_matrix_level(
    risk_matrix_level_id: int,
    payload: RiskMatrixLevelUpdate,
    current_user: User = Depends(_manage_risks),
    db: Session = Depends(get_db),
) -> RiskMatrixLevelResponse:
    level = risk_service.update_risk_matrix_level(db, current_user, risk_matrix_level_id, payload)
    return RiskMatrixLevelResponse.model_validate(level)


@router.post("/risk-assessments", response_model=RiskAssessmentResponse, status_code=201)
def create_risk_assessment(
    payload: RiskAssessmentCreate,
    current_user: User = Depends(_raise_risks),
    db: Session = Depends(get_db),
) -> RiskAssessmentResponse:
    risk_assessment = risk_service.create_risk_assessment(db, current_user, payload)
    return RiskAssessmentResponse.model_validate(risk_assessment)


@router.get("/risk-assessments", response_model=PaginatedResponse[RiskAssessmentResponse])
def list_risk_assessments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    property_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[RiskAssessmentResponse]:
    items, total = risk_service.list_risk_assessments(
        db,
        current_user,
        page=page,
        page_size=page_size,
        status=status,
        risk_level=risk_level,
        property_id=property_id,
    )
    return PaginatedResponse(
        items=[RiskAssessmentResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/risk-assessments/{risk_assessment_id}", response_model=RiskAssessmentResponse)
def get_risk_assessment(
    risk_assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskAssessmentResponse:
    risk_assessment = risk_service.get_risk_assessment(db, current_user, risk_assessment_id)
    return RiskAssessmentResponse.model_validate(risk_assessment)


@router.patch("/risk-assessments/{risk_assessment_id}", response_model=RiskAssessmentResponse)
def update_risk_assessment(
    risk_assessment_id: int,
    payload: RiskAssessmentUpdate,
    current_user: User = Depends(_manage_risks),
    db: Session = Depends(get_db),
) -> RiskAssessmentResponse:
    risk_assessment = risk_service.update_risk_assessment(db, current_user, risk_assessment_id, payload)
    return RiskAssessmentResponse.model_validate(risk_assessment)
