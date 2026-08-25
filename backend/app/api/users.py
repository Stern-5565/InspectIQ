"""
GET /api/users - added for the Maintenance module's "assign to" picker (app/api/maintenance.py's
assign_issue lets AssignedUserId be any company user, per scope §17: assignment isn't restricted
to the "Maintenance" role), not part of any earlier phase. View-only, no role restriction - same
"any company member can see their colleagues" reasoning as every other view endpoint in this
project. No create/update/delete here - user management (inviting/deactivating a user) is
Admin Settings' job, a still-unbuilt Phase 16 page, not this endpoint's.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.repositories import user_repository
from app.schemas.user import UserResponse
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    include_inactive: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    users = user_repository.list_users_for_company(db, current_user.CompanyId, include_inactive=include_inactive)
    return [UserResponse.from_user(u) for u in users]
