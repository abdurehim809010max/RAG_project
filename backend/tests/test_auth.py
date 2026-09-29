import pytest
from fastapi import HTTPException

from backend.app.api.v1.endpoints.auth import clear_users, current_user, login, register
from backend.app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from backend.app.models.user import UserLogin, UserRegistration


@pytest.fixture(autouse=True)
def reset_users(monkeypatch):
    clear_users()
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-only-secret")
    yield
    clear_users()


def test_password_hash_is_not_plaintext():
    password_hash = hash_password("correct horse battery staple")
    assert password_hash != "correct horse battery staple"
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_access_token_round_trip_and_tamper_detection():
    token = create_access_token("user@example.com", expires_in=60)
    assert decode_access_token(token)["sub"] == "user@example.com"
    with pytest.raises(ValueError, match="invalid access token"):
        decode_access_token(token[:-1] + ("a" if token[-1] != "a" else "b"))


def test_register_login_and_current_user():
    user = register(UserRegistration(email="User@Example.com", password="password123"))
    assert user.email == "user@example.com"
    assert not hasattr(user, "password_hash")

    token = login(UserLogin(email="user@example.com", password="password123"))
    authenticated = current_user(f"Bearer {token.access_token}")
    assert authenticated.email == user.email


def test_duplicate_registration_and_bad_login_are_rejected():
    register(UserRegistration(email="user@example.com", password="password123"))
    with pytest.raises(HTTPException) as duplicate:
        register(UserRegistration(email="USER@example.com", password="password456"))
    assert duplicate.value.status_code == 409

    with pytest.raises(HTTPException) as bad_login:
        login(UserLogin(email="user@example.com", password="wrongpass"))
    assert bad_login.value.status_code == 401


def test_missing_authentication_is_rejected():
    with pytest.raises(HTTPException) as error:
        current_user(None)
    assert error.value.status_code == 401
