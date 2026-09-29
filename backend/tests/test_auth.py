def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "User@Example.com", "password": "password123"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert "hashed_password" not in body


def test_register_duplicate_returns_conflict(client):
    payload = {"email": "user@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "USER@example.com", "password": "password456"},
    )

    assert response.status_code == 409


def test_register_bad_email_returns_validation_error(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "password123"},
    )

    assert response.status_code == 422


def test_login_success(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "USER@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_wrong_password_returns_unauthorized(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_login_unknown_email_returns_unauthorized(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "password123"},
    )

    assert response.status_code == 401


def test_me_with_token_returns_current_user(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_me_without_token_returns_unauthorized(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
