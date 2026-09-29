"""Authentication endpoints.

The in-memory repository is deliberately isolated here until the database
adapter owned by Person 1 is available. It is suitable for local development
and tests, but must be replaced for production persistence.
"""

from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from backend.app.core.security import (
    AuthenticationError,
    create_access_token,
    decode_access_token,
    hash_password,
    utc_now,
    verify_password,
)
from backend.app.models.user import (
    TokenResponse,
    User,
    UserLogin,
    UserPublic,
    UserRegistration,
)

router = APIRouter()
_USERS_BY_EMAIL: dict[str, User] = {}
_TOKEN_EXPIRE_SECONDS = 30 * 60


def _public_user(user: User) -> UserPublic:
    return UserPublic(**user.model_dump(exclude={"password_hash"}))


def _find_user(email: str) -> User | None:
    return _USERS_BY_EMAIL.get(email.casefold())


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        claims = decode_access_token(authorization[7:].strip())
    except (AuthenticationError, RuntimeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from None
    user = _find_user(claims["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    return user


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegistration) -> UserPublic:
    email = payload.email.casefold()
    if _find_user(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    user = User(
        id=secrets.token_urlsafe(16),
        email=email,
        password_hash=hash_password(payload.password),
        created_at=utc_now(),
    )
    _USERS_BY_EMAIL[email] = user
    return _public_user(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin) -> TokenResponse:
    user = _find_user(payload.email)
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(
        access_token=create_access_token(
            user.email, expires_delta=timedelta(seconds=_TOKEN_EXPIRE_SECONDS)
        ),
        expires_in=_TOKEN_EXPIRE_SECONDS,
    )


@router.get("/me", response_model=UserPublic)
def current_user(user: User = Depends(get_current_user)) -> UserPublic:
    return _public_user(user)


def clear_users() -> None:
    """Clear the development repository between tests or local sessions."""
    _USERS_BY_EMAIL.clear()
