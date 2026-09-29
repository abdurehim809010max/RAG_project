from datetime import timedelta

import pytest

from backend.app.core.security import (
    AuthenticationError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_verify_roundtrip():
    password_hash = hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert verify_password("correct horse battery staple", password_hash)


def test_verify_rejects_wrong_password():
    password_hash = hash_password("correct horse battery staple")

    assert not verify_password("wrong password", password_hash)


def test_token_create_decode_roundtrip():
    token = create_access_token("user@example.com")

    assert decode_access_token(token)["sub"] == "user@example.com"


def test_expired_token_is_rejected():
    token = create_access_token("user@example.com", expires_delta=timedelta(seconds=-1))

    with pytest.raises(AuthenticationError, match="expired"):
        decode_access_token(token)


def test_tampered_token_is_rejected():
    token = create_access_token("user@example.com")
    tampered_token = token[:-1] + ("a" if token[-1] != "a" else "b")

    with pytest.raises(AuthenticationError, match="invalid"):
        decode_access_token(tampered_token)