"""
Service-layer tests for Centrifugo subscription-token gating.

Uses the real CentrifugoService with an in-memory FakeOrmManager so the
membership check runs without a database.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from jose import jwt
from tests.conftest import FakeOrmManager

from src.backend.app.services.centrifugo.service_v1 import CentrifugoService
from src.backend.config.main import settings


@pytest.fixture
def orm() -> FakeOrmManager:
    return FakeOrmManager()


@pytest.fixture
def service(orm: FakeOrmManager) -> CentrifugoService:
    return CentrifugoService(orm)


def _add_membership(orm: FakeOrmManager, channel_id: UUID, user_id: UUID) -> None:
    from types import SimpleNamespace
    orm.channel_member._members.append(
        SimpleNamespace(channel_id=channel_id, user_id=user_id)
    )


# ---------------------------------------------------------------------------
#  is_channel_member
# ---------------------------------------------------------------------------
class TestIsChannelMember:
    @pytest.mark.asyncio
    async def test_member_returns_true(self, service, orm):
        channel_id = uuid4()
        user_id = uuid4()
        _add_membership(orm, channel_id, user_id)
        assert await service.is_channel_member(channel_id, user_id) is True

    @pytest.mark.asyncio
    async def test_non_member_returns_false(self, service):
        channel_id = uuid4()
        user_id = uuid4()
        assert await service.is_channel_member(channel_id, user_id) is False


# ---------------------------------------------------------------------------
#  create_subscription_token
# ---------------------------------------------------------------------------
class TestCreateSubscriptionToken:
    @pytest.mark.asyncio
    async def test_member_receives_valid_token(self, service, orm):
        channel_id = uuid4()
        user_id = uuid4()
        _add_membership(orm, channel_id, user_id)

        token = await service.create_subscription_token(user_id, channel_id)

        payload = jwt.decode(
            token,
            settings.app.CENTRIFUGO_CLIENT_SUBSCRIPTION_TOKEN_HMAC_SECRET_KEY,
            algorithms=["HS256"],
        )
        assert payload["sub"] == str(user_id)
        assert payload["channel"] == f"chat:{channel_id}"

    @pytest.mark.asyncio
    async def test_non_member_raises_403(self, service):
        channel_id = uuid4()
        user_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_subscription_token(user_id, channel_id)

        assert exc_info.value.status_code == 403
        assert "not a member" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_personal_channel_for_owner_succeeds(self, service):
        user_id = uuid4()
        token = await service.create_subscription_token(user_id, f"user#{user_id}")

        payload = jwt.decode(
            token,
            settings.app.CENTRIFUGO_CLIENT_SUBSCRIPTION_TOKEN_HMAC_SECRET_KEY,
            algorithms=["HS256"],
        )
        assert payload["channel"] == f"user#{user_id}"

    @pytest.mark.asyncio
    async def test_personal_channel_for_other_user_raises_403(self, service):
        user_id = uuid4()
        other_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_subscription_token(user_id, f"user#{other_id}")

        assert exc_info.value.status_code == 403
        assert "personal channel" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_membership_is_checked_per_channel(self, service, orm):
        channel_a = uuid4()
        channel_b = uuid4()
        user_id = uuid4()
        _add_membership(orm, channel_a, user_id)

        # Allowed on channel A
        assert await service.create_subscription_token(user_id, channel_a)

        # Denied on channel B
        with pytest.raises(HTTPException) as exc_info:
            await service.create_subscription_token(user_id, channel_b)
        assert exc_info.value.status_code == 403
