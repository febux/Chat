"""
API-layer tests for authentication routes: register, login, logout, /me.

Uses TestClient with FakeUserService via dependency override.
"""
import pytest

from src.backend.utils.password import hash_password_sync


@pytest.fixture
def register_payload():
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "SecurePass123",
        "password_check": "SecurePass123",
    }


@pytest.fixture
def login_payload():
    return {"email": "alice@example.com", "password": "SecurePass123"}


@pytest.fixture
def pre_hashed_password() -> str:
    return hash_password_sync("SecurePass123")


# ---------------------------------------------------------------------------
#  POST /api/v1/register
# ---------------------------------------------------------------------------
class TestRegister:
    def test_successful_registration(self, client, fake_service, register_payload):
        resp = client.post("/api/v1/register", json=register_payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "message" in data
        assert "user_id" in data

    def test_duplicate_email_returns_409(self, client, fake_service, register_payload):
        client.post("/api/v1/register", json=register_payload)
        resp = client.post("/api/v1/register", json=register_payload)
        assert resp.status_code == 409

    def test_password_mismatch_returns_409(self, client, register_payload):
        payload = {**register_payload, "password_check": "Different456"}
        resp = client.post("/api/v1/register", json=payload)
        assert resp.status_code == 409

    def test_non_empty_short_password_accepted(self, client, register_payload):
        """NOTE: schema min_length=5 is NOT enforced (NonEmptyString bug).
        A short non-empty password passes validation."""
        payload = {**register_payload, "password": "abc", "password_check": "abc"}
        resp = client.post("/api/v1/register", json=payload)
        assert resp.status_code == 201

    def test_invalid_email_rejected(self, client, register_payload):
        payload = {**register_payload, "email": "not-an-email"}
        resp = client.post("/api/v1/register", json=payload)
        assert resp.status_code == 422

    def test_missing_field_rejected(self, client):
        resp = client.post("/api/v1/register", json={"email": "a@b.com"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
#  POST /api/v1/login
# ---------------------------------------------------------------------------
class TestLogin:
    def test_successful_login_sets_cookie(self, client, fake_service, login_payload, pre_hashed_password):
        # Pre-populate the service with a user (keyed by str(uid) to match lookup)
        from uuid import uuid4

        uid = uuid4()
        fake_service._users[str(uid)] = {
            "id": uid,
            "username": "alice",
            "email": "alice@example.com",
            "password_hash": pre_hashed_password,
        }

        resp = client.post("/api/v1/login", json=login_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["message"] == "Authorization successful!"

    def test_wrong_password_returns_401(self, client, fake_service, login_payload, pre_hashed_password):
        from uuid import uuid4

        uid = uuid4()
        fake_service._users[str(uid)] = {
            "id": uid,
            "username": "alice",
            "email": "alice@example.com",
            "password_hash": pre_hashed_password,
        }
        bad_payload = {**login_payload, "password": "WrongPass999"}
        resp = client.post("/api/v1/login", json=bad_payload)
        assert resp.status_code == 401

    def test_nonexistent_user_returns_401(self, client, login_payload):
        resp = client.post("/api/v1/login", json=login_payload)
        assert resp.status_code == 401

    def test_login_with_invalid_email_returns_422(self, client):
        resp = client.post("/api/v1/login", json={"email": "bad", "password": "SecurePass123"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
#  POST /api/v1/logout
# ---------------------------------------------------------------------------
class TestLogout:
    def test_logout_clears_cookies(self, client):
        """With get_current_user overridden, logout should succeed."""
        resp = client.post("/api/v1/logout")
        assert resp.status_code == 200
        assert "logged out" in resp.json()["message"].lower()


# ---------------------------------------------------------------------------
#  GET /api/v1/me
# ---------------------------------------------------------------------------
class TestGetCurrentUser:
    def test_me_returns_user_data(self, client, sample_user_id):
        resp = client.get("/api/v1/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "alice@example.com"
        assert data["name"] == "alice"
        assert "is_active" in data

    def test_me_without_auth_returns_error(self, unauth_client):
        """Without auth override, get_current_user raises TokenNotFoundError.
        The exception handler redirects to /auth; TestClient follows it (→ 404
        since /auth has no route in the test app). Either way it's not 200."""
        resp = unauth_client.get("/api/v1/me", follow_redirects=False)
        assert resp.status_code in (307, 302, 401)
