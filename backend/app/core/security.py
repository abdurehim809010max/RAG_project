"""Authentication primitives shared by the auth API and protected routes."""

from __future__ import annotations

from datetime import datetime, timezone
from datetime import timedelta
from typing import Any

import bcrypt
import jwt
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError as PyJWTInvalidTokenError

from backend.app.core.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class AuthenticationError(ValueError):
    """Raised when a credential or token cannot be trusted."""


class TokenExpiredError(AuthenticationError):
    """Raised when an access token's expiration time has passed."""


class InvalidTokenError(AuthenticationError):
    """Raised when an access token cannot be decoded or verified."""


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password must not be empty")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token for ``subject``.

    Args:
        subject: Stable user identifier stored in the token's ``sub`` claim.
        expires_delta: Optional lifetime override. If omitted, the cached
            application settings determine the lifetime.

    Raises:
        ValueError: If ``subject`` is empty.
    """
    if not subject:
        raise ValueError("token subject must not be empty")
    settings = get_settings()
    lifetime = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": datetime.now(timezone.utc) + lifetime}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token using application settings.

    Raises:
        TokenExpiredError: If the token has expired.
        InvalidTokenError: If the token is malformed, unsigned, or invalid.
    """
    try:
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError as error:
        raise TokenExpiredError("access token has expired") from error
    except PyJWTInvalidTokenError as error:
        raise InvalidTokenError("invalid access token") from error

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise InvalidTokenError("access token subject is missing")
    return payload


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
