"""
Read-only for this phase - scope §9 says "the administrator should eventually be able to
create and edit inspection templates," and the scope's own phase list treats the inspection
engine (starting/answering/submitting) as the next phase after this one, not template
authoring. Building template CRUD now would be scope creep ahead of an actual need; these two
endpoints exist because Phase 8 (the inspection engine) needs a template to read from to start
an inspection.

Open to any authenticated company user (view only, no mutation exists yet) - same reasoning as
Properties: an Inspector needs to see which templates are available and their structure to
conduct an inspection.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.inspection_template import InspectionTemplateDetailResponse, InspectionTemplateResponse
from app.security.dependencies import get_current_user
from app.services import inspection_template_service

router = APIRouter(prefix="/inspection-templates", tags=["inspection-templates"])


@router.get("", response_model=list[InspectionTemplateResponse])
def list_templates(
    include_inactive: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InspectionTemplateResponse]:
    templates = inspection_template_service.list_templates(
        db, current_user, include_inactive=include_inactive
    )
    return [InspectionTemplateResponse.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=InspectionTemplateDetailResponse)
def get_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InspectionTemplateDetailResponse:
    template = inspection_template_service.get_template(db, current_user, template_id)
    return InspectionTemplateDetailResponse.from_template(template)
