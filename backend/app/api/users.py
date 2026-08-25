"""
GET /api/users - added for the Maintenance module's "assign to" picker (app/api/maintenance.py's
assign_issue lets AssignedUserId be any company user, per scope §17: assignment isn't restricted
to the "Maintenance" role). View-only, no role restriction - same "any company member can see
their colleagues" reasoning as every other view endpoint in this project. Now also routes through
user_service (it originally called user_repository directly - a minor exception to this
project's "routes call services" layering, acceptable when list_users_for_company genuinely had
no business logic; now that create/update exist with real logic, routing list through the same
service keeps every endpoint in this router consistent).

POST/PATCH are Admin Settings' own addition (see app/services/user_service.py's module
docstring) - Administrator-ONLY, the first tier in this project that excludes Manager. GET
/{user_id} was added alongside them for the standalone module's detail page (the list response
already has everything a row needs, but a direct link/refresh needs its own lookup).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.security import roles
from app.security.dependencies import get_current_user, require_roles
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

_manage_users = require_roles(roles.ADMINISTRATOR)


@router.get("", response_model=list[UserResponse])
def list_users(
    include_inactive: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    users = user_service.list_users(db, current_user, include_inactive=include_inactive)
    return [UserResponse.from_user(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    user = user_service.get_user(db, current_user, user_id)
    return UserResponse.from_user(user)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(_manage_users),
    db: Session = Depends(get_db),
) -> UserResponse:
    user = user_service.create_user(db, current_user, payload)
    return UserResponse.from_user(user)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(_manage_users),
    db: Session = Depends(get_db),
) -> UserResponse:
    user = user_service.update_user(db, current_user, user_id, payload)
    return UserResponse.from_user(user)
