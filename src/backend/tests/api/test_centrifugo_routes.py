"""
API-layer tests for the Centrifugo subscription-token route.

Uses TestClient with the real CentrifugoService backed by fake repositories.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from jose import jwt
from starlette.testclient import TestClient
from tests.conftest import FakeOrmManager

from src.backend.config.main import settings


@pytest.fixture
def centrifugo_orm() -> FakeOrmManager:
    return FakeOrmManager()


# ---------------------------------------------------------------------------
#  POST /api/v1/centrifugo/subscription-token
# ---------------------------------------------------------------------------
class TestGetSubscriptionToken:
    def test_member_channel_returns_token(self, centrifugo_client, centrifugo_orm, sample_user_id: UUID):
        channel_id = uuid4()
        from types import SimpleNamespace
        centrifugo_orm.channel_member._members.append(
            SimpleNamespace(channel_id=channel_id, user_id=sample_user_id)
        )

        resp = centrifugo_client.post(
            "/api/v1/centrifugo/subscription-token",
            json={"channel_id": str(channel_id)},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data

        payload = jwt.decode(
            data["token"],
            settings.app.CENTRIFUGO_CLIENT_SUBSCRIPTION_TOKEN_HMAC_SECRET_KEY,
            algorithms=["HS256"],
        )
        assert payload["sub"] == str(sample_user_id)
        assert payload["channel"] == f"chat:{channel_id}"

    def test_non_member_channel_returns_403(self, centrifugo_client):
        channel_id = uuid4()

        resp = centrifugo_client.post(
            "/api/v1/centrifugo/subscription-token",
            json={"channel_id": str(channel_id)},
        )

        assert resp.status_code == 403
        assert "not a member" in resp.json()["detail"].lower()

    def test_unauthenticated_request_rejected(self, unauth_client: TestClient):
        resp = unauth_client.post(
            "/api/v1/centrifugo/subscription-token",
            json={"channel_id": str(uuid4())},
        )
        assert resp.status_code == 401

    def test_invalid_channel_id_returns_422(self, centrifugo_client):
        resp = centrifugo_client.post(
            "/api/v1/centrifugo/subscription-token",
            json={"channel_id": "not-a-uuid"},
        )
        assert resp.status_code == 422
