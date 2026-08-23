from datetime import datetime, timezone

from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.models.user import User
from app.repositories.user_repository import get_user_by_email, get_user_by_id
from app.security.jwt import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.security.password import verify_password

# Deliberately the same generic message whether the email doesn't exist, the password is
# wrong, or the account is disabled - never reveal which one was incorrect. This is a
# standard security tradeoff (OWASP: don't let login responses enable account enumeration)
# accepted over the UX benefit of a clearer "your account is disabled" message.
_INVALID_CREDENTIALS_MESSAGE = "Incorrect email or password."


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.PasswordHash):
        raise UnauthorizedError(_INVALID_CREDENTIALS_MESSAGE)
    if not user.IsActive:
        raise UnauthorizedError(_INVALID_CREDENTIALS_MESSAGE)

    user.LastLoginAt = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def issue_tokens(user: User) -> tuple[str, str]:
    return create_access_token(user.UserId), create_refresh_token(user.UserId)


def get_user_from_refresh_token(db: Session, refresh_token: str) -> User:
    try:
        payload = decode_token(refresh_token)
    except PyJWTError:
        raise UnauthorizedError("Invalid or expired refresh token.")

    if payload.get("type") != REFRESH_TOKEN_TYPE:
        raise UnauthorizedError("Invalid token type.")

    user = get_user_by_id(db, int(payload["sub"]))
    if user is None or not user.IsActive:
        raise UnauthorizedError("User account is inactive or no longer exists.")
    return user
