"""
API-layer tests for admin routes: authentication/authorization guards.

Verifies that /admin/api/v1/** and /admin/api/v2/** are only accessible to
authenticated admin users.
"""
from uuid import uuid4

from starlette.testclient import TestClient
from tests.conftest import FakeUserService

from src.backend.schemas.users.user_get import User


# ---------------------------------------------------------------------------
#  Admin v1 users routes
# ---------------------------------------------------------------------------
class TestAdminV1UsersAuth:
    def test_unauthenticated_request_returns_401(self, unauth_client: TestClient):
        resp = unauth_client.get("/admin/api/v1/users")
        assert resp.status_code == 401

    def test_regular_user_request_returns_403(self, client: TestClient):
        resp = client.get("/admin/api/v1/users")
        assert resp.status_code == 403

    def test_admin_user_can_list_users(self, admin_client: TestClient, fake_service: FakeUserService):
        uid = uuid4()
        fake_service._users[str(uid)] = {
            "id": uid,
            "username": "bob",
            "email": "bob@example.com",
            "password_hash": "x",
        }
        resp = admin_client.get("/admin/api/v1/users?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_admin_user_can_get_user_by_id(self, admin_client: TestClient, fake_service: FakeUserService):
        uid = uuid4()
        fake_service._users[str(uid)] = {
            "id": uid,
            "username": "bob",
            "email": "bob@example.com",
            "password_hash": "x",
        }
        resp = admin_client.get(f"/admin/api/v1/users/{uid}")
        assert resp.status_code == 200
        assert resp.json()["email"] == "bob@example.com"


# ---------------------------------------------------------------------------
#  Admin v2 maintenance routes
# ---------------------------------------------------------------------------
class TestAdminV2MaintenanceAuth:
    def test_unauthenticated_healthcheck_returns_401(self, unauth_client: TestClient):
        resp = unauth_client.get("/admin/api/v2/healthcheck")
        assert resp.status_code == 401

    def test_unauthenticated_metrics_returns_401(self, unauth_client: TestClient):
        resp = unauth_client.get("/admin/api/v2/metrics")
        assert resp.status_code == 401

    def test_regular_user_healthcheck_returns_403(self, client: TestClient):
        resp = client.get("/admin/api/v2/healthcheck")
        assert resp.status_code == 403

    def test_regular_user_metrics_returns_403(self, client: TestClient):
        resp = client.get("/admin/api/v2/metrics")
        assert resp.status_code == 403

    def test_admin_user_can_access_healthcheck(self, admin_client: TestClient):
        resp = admin_client.get("/admin/api/v2/healthcheck")
        assert resp.status_code == 200

    def test_admin_user_can_access_metrics(self, admin_client: TestClient):
        resp = admin_client.get("/admin/api/v2/metrics")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
#  Admin flag via token/cookie path (integration-ish)
# ---------------------------------------------------------------------------
class TestAdminFlagInUserSchema:
    def test_user_schema_defaults_is_admin_to_false(self, sample_user: User):
        assert sample_user.is_admin is False

    def test_user_schema_can_set_is_admin_true(self):
        user = User(
            id=uuid4(),
            username="admin",
            email="admin@example.com",
            is_admin=True,
            created_at=__import__("datetime").datetime.now(),
            updated_at=__import__("datetime").datetime.now(),
        )
        assert user.is_admin is True
