"""Authentication primitives shared by the auth API and protected routes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import bcrypt


class AuthenticationError(ValueError):
    """Raised when a credential or token cannot be trusted."""


def _secret() -> bytes:
    value = os.getenv("AUTH_SECRET_KEY") or os.getenv("SECRET_KEY")
    if not value:
        raise RuntimeError("AUTH_SECRET_KEY must be configured")
    return value.encode("utf-8")


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


def _encode_part(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_part(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(subject: str, expires_in: int | None = None, **claims: Any) -> str:
    if not subject:
        raise ValueError("token subject must not be empty")
    lifetime = expires_in or int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")) * 60
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "iat": now, "exp": now + lifetime, **claims}
    encoded_header = _encode_part(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _encode_part(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(_secret(), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_encode_part(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        header = json.loads(_decode_part(encoded_header))
        payload = json.loads(_decode_part(encoded_payload))
        signature = _decode_part(encoded_signature)
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        raise AuthenticationError("invalid access token") from None

    if header != {"alg": "HS256", "typ": "JWT"}:
        raise AuthenticationError("unsupported access token")
    expected = hmac.new(
        _secret(), f"{encoded_header}.{encoded_payload}".encode("ascii"), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(signature, expected):
        raise AuthenticationError("invalid access token")
    if not isinstance(payload.get("sub"), str) or not payload["sub"]:
        raise AuthenticationError("token subject is missing")
    if not isinstance(payload.get("exp"), int) or payload["exp"] <= int(time.time()):
        raise AuthenticationError("access token has expired")
    return payload


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
