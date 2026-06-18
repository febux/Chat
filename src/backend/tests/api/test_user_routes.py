"""
API-layer tests for user management routes: list contacts, get by id,
contact by email, ping.

Uses TestClient with FakeUserService via dependency override.
"""
from uuid import uuid4

import pytest
from starlette.testclient import TestClient
from tests.conftest import _build_test_app


# ---------------------------------------------------------------------------
#  GET /api/v1/users  — list contacts
# ---------------------------------------------------------------------------
class TestGetUsers:
    def test_returns_list_of_users(self, client, fake_service):
        fake_service._users["1"] = {
            "id": uuid4(),
            "username": "bob",
            "email": "bob@example.com",
            "password_hash": "x",
        }
        resp = client.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_empty_contacts_returns_empty_list(self, client):
        resp = client.get("/api/v1/users")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
#  GET /api/v1/users/{user_id}  — get by id
# ---------------------------------------------------------------------------
class TestGetUserById:
    def test_get_existing_user(self, client, fake_service):
        uid = uuid4()
        fake_service._users[str(uid)] = {
            "id": uid,
            "username": "bob",
            "email": "bob@example.com",
            "password_hash": "x",
        }
        resp = client.get(f"/api/v1/users/{uid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "bob@example.com"

    def test_get_nonexistent_user_returns_500(self, fake_service, sample_user):
        """get_by_id returns None; route has response_model=User which rejects None.
        This is a known issue — the route should return 404, not 500."""
        app = _build_test_app(fake_service, current_user=sample_user)
        client_no_raise = TestClient(app, raise_server_exceptions=False)
        resp = client_no_raise.get(f"/api/v1/users/{uuid4()}")
        assert resp.status_code == 500

    def test_invalid_uuid_returns_422(self, client):
        resp = client.get("/api/v1/users/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
#  POST /api/v1/users/contact  — contact by email (JSON body)
# ---------------------------------------------------------------------------
class TestContactUserByEmail:
    def test_new_contact_returns_201(self, client, fake_service, sample_user_id):
        contact_id = uuid4()
        fake_service._users[str(contact_id)] = {
            "id": contact_id,
            "username": "bob",
            "email": "bob@example.com",
            "password_hash": "x",
        }
        resp = client.post("/api/v1/users/contact", json={"email": "bob@example.com"})
        assert resp.status_code == 201
        assert "successfully" in resp.json()["detail"]

    def test_duplicate_contact_returns_200(self, client, fake_service, sample_user_id):
        contact_id = uuid4()
        fake_service._users[str(contact_id)] = {
            "id": contact_id,
            "username": "bob",
            "email": "bob@example.com",
            "password_hash": "x",
        }
        client.post("/api/v1/users/contact", json={"email": "bob@example.com"})
        resp = client.post("/api/v1/users/contact", json={"email": "bob@example.com"})
        assert resp.status_code == 200
        assert "already" in resp.json()["detail"]

    def test_self_contact_returns_200(self, client, fake_service, sample_user_id):
        """Self-contact is rejected — service returns False → 200."""
        fake_service._users[str(sample_user_id)] = {
            "id": sample_user_id,
            "username": "alice",
            "email": "alice@example.com",
            "password_hash": "x",
        }
        resp = client.post("/api/v1/users/contact", json={"email": "alice@example.com"})
        assert resp.status_code == 200

    def test_nonexistent_contact_returns_200(self, client):
        """Contact email doesn't exist — service returns False → 200."""
        resp = client.post("/api/v1/users/contact", json={"email": "ghost@example.com"})
        assert resp.status_code == 200

    def test_invalid_email_returns_422(self, client):
        """Email is validated as EmailStr — a malformed value is rejected before
        the service is ever called."""
        resp = client.post("/api/v1/users/contact", json={"email": "not-an-email"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
#  POST /api/v1/users/ping  — heartbeat
# ---------------------------------------------------------------------------
class TestUserPing:
    def test_ping_returns_ok(self, client, fake_service, sample_user_id):
        resp = client.post("/api/v1/users/ping")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        assert sample_user_id in fake_service.ping_called

    def test_multiple_pings(self, client, fake_service, sample_user_id):
        for _ in range(3):
            resp = client.post("/api/v1/users/ping")
            assert resp.status_code == 200
        assert fake_service.ping_called.count(sample_user_id) == 3
