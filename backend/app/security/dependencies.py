from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.database.session import get_db
from app.models.user import User
from app.repositories.user_repository import get_user_by_id
from app.security.jwt import ACCESS_TOKEN_TYPE, decode_token

# tokenUrl is only used for OpenAPI's "Authorize" button metadata - login itself takes a JSON
# body (LoginRequest), not an OAuth2 form. auto_error=False so a missing token goes through
# our own UnauthorizedError/exception-handler path instead of FastAPI's default response shape.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if token is None:
        raise UnauthorizedError("Not authenticated.")

    try:
        payload = decode_token(token)
    except PyJWTError:
        raise UnauthorizedError("Invalid or expired token.")

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise UnauthorizedError("Invalid token type.")

    user_id = int(payload["sub"])
    # Loaded fresh from the database on every single request, never trusted from the token
    # payload - an already-issued token must stop working the instant its user is deactivated,
    # not just once the token naturally expires. Same pattern that caught a real bug in
    # PropertyManager (an access token kept working after IsActive flipped, until this exact
    # re-check was added).
    user = get_user_by_id(db, user_id)
    if user is None or not user.IsActive:
        raise UnauthorizedError("User account is inactive or no longer exists.")
    return user


def require_roles(*role_names: str):
    """Factory dependency: Depends(require_roles(roles.ADMINISTRATOR, roles.MANAGER))."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        user_role_names = {role.RoleName for role in current_user.roles}
        if not user_role_names.intersection(role_names):
            raise ForbiddenError("You do not have permission to perform this action.")
        return current_user

    return dependency
