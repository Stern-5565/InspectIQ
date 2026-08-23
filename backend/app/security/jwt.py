"""
JWT encode/decode. Tokens carry only `sub` (user id) and `type` - deliberately NOT CompanyId.
PROJECT_PLAN.md §7 allowed embedding CompanyId "for convenience," but get_current_user always
reloads the full User from the database on every request anyway (see security/dependencies.py),
so a token-embedded CompanyId would just be extra surface area for zero actual benefit - never
trusted, never needed. Simpler to just not put it there.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as pyjwt

from app.core.config import settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def _create_token(user_id: int, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _create_token(
        user_id, ACCESS_TOKEN_TYPE, timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        user_id, REFRESH_TOKEN_TYPE, timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )


def decode_token(token: str) -> dict[str, Any]:
    # Raises jwt.PyJWTError subclasses on invalid/expired tokens - callers convert this to
    # UnauthorizedError, never let a raw JWT exception escape to the client.
    return pyjwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
