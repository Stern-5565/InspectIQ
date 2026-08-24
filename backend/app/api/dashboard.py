"""View-only, any company member - a dashboard has no mutate action of its own. See
app/services/dashboard_service.py's module docstring for the full reasoning.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.security.dependencies import get_current_user
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    return dashboard_service.get_dashboard(db, current_user)
