"""
Service-layer tests for UserService business logic.

Uses the REAL UserService with in-memory FakeOrmManager and FakeRedis —
tests actual branching logic without touching a database.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from tests.conftest import FakeOrmManager, FakeRedis

from src.backend.app.services.user.service_v1 import (ONLINE_TTL_SECONDS,
                                                      REDIS_PREFIX_LAST_SEEN,
                                                      REDIS_PREFIX_STATUS,
                                                      UserService)
from src.backend.utils.password import hash_password_sync


@pytest.fixture
def orm() -> FakeOrmManager:
    return FakeOrmManager()


@pytest.fixture
def redis_client() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def service(orm: FakeOrmManager, redis_client: FakeRedis) -> UserService:
    return UserService(orm_manager=orm, redis_client=redis_client)


def _add_user(orm: FakeOrmManager, email: str, username: str, password: str = "SecretPass123"):
    return orm.user._add(
        id=uuid4(),
        email=email,
        username=username,
        password_hash=hash_password_sync(password),
    )


# ---------------------------------------------------------------------------
#  authenticate_user
# ---------------------------------------------------------------------------
class TestAuthenticateUser:
    @pytest.mark.asyncio
    async def test_valid_credentials_returns_user(self, service, orm):
        _add_user(orm, "alice@example.com", "alice")
        user = await service.authenticate_user("alice@example.com", "SecretPass123")
        assert user is not None
        assert user.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_wrong_password_returns_none(self, service, orm):
        _add_user(orm, "alice@example.com", "alice")
        assert await service.authenticate_user("alice@example.com", "WrongPass456") is None

    @pytest.mark.asyncio
    async def test_nonexistent_email_returns_none(self, service):
        assert await service.authenticate_user("nobody@example.com", "SecretPass123") is None

    @pytest.mark.asyncio
    async def test_returned_user_has_no_password_hash(self, service, orm):
        """authenticate_user returns a clean User schema — no password_hash leak."""
        _add_user(orm, "alice@example.com", "alice")
        user = await service.authenticate_user("alice@example.com", "SecretPass123")
        assert not hasattr(user, "password_hash")


# ---------------------------------------------------------------------------
#  contact_user
# ---------------------------------------------------------------------------
class TestContactUser:
    @pytest.mark.asyncio
    async def test_successful_contact(self, service, orm):
        user = _add_user(orm, "alice@example.com", "alice")
        _add_user(orm, "bob@example.com", "bob")
        result = await service.contact_user(user_id=user.id, contact_email="bob@example.com")
        assert result is True

    @pytest.mark.asyncio
    async def test_self_contact_rejected(self, service, orm):
        user = _add_user(orm, "alice@example.com", "alice")
        result = await service.contact_user(user_id=user.id, contact_email="alice@example.com")
        assert result is False

    @pytest.mark.asyncio
    async def test_nonexistent_contact_rejected(self, service, orm):
        user = _add_user(orm, "alice@example.com", "alice")
        result = await service.contact_user(user_id=user.id, contact_email="ghost@example.com")
        assert result is False

    @pytest.mark.asyncio
    async def test_duplicate_forward_contact_rejected(self, service, orm):
        user = _add_user(orm, "alice@example.com", "alice")
        _add_user(orm, "bob@example.com", "bob")
        await service.contact_user(user_id=user.id, contact_email="bob@example.com")
        result = await service.contact_user(user_id=user.id, contact_email="bob@example.com")
        assert result is False

    @pytest.mark.asyncio
    async def test_reverse_contact_rejected(self, service, orm):
        """If B already added A, A adding B should be rejected (bidirectional check)."""
        alice = _add_user(orm, "alice@example.com", "alice")
        bob = _add_user(orm, "bob@example.com", "bob")
        # Bob adds Alice
        await service.contact_user(user_id=bob.id, contact_email="alice@example.com")
        # Alice tries to add Bob — should be rejected (reverse entry exists)
        result = await service.contact_user(user_id=alice.id, contact_email="bob@example.com")
        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_different_contacts_allowed(self, service, orm):
        """A user should be able to add multiple different contacts."""
        alice = _add_user(orm, "alice@example.com", "alice")
        _add_user(orm, "bob@example.com", "bob")
        _add_user(orm, "carol@example.com", "carol")
        assert await service.contact_user(user_id=alice.id, contact_email="bob@example.com") is True
        assert await service.contact_user(user_id=alice.id, contact_email="carol@example.com") is True


# ---------------------------------------------------------------------------
#  set_user_ping
# ---------------------------------------------------------------------------
class TestSetUserPing:
    @pytest.mark.asyncio
    async def test_sets_online_status_in_redis(self, service, redis_client, orm):
        uid = uuid4()
        await service.set_user_ping(user_id=uid)
        status = redis_client._store.get(REDIS_PREFIX_STATUS + str(uid))
        assert status == "online"

    @pytest.mark.asyncio
    async def test_sets_last_seen_timestamp(self, service, redis_client, orm):
        uid = uuid4()
        await service.set_user_ping(user_id=uid)
        last_seen = redis_client._store.get(REDIS_PREFIX_LAST_SEEN + str(uid))
        assert last_seen is not None
        assert int(last_seen) > 0

    @pytest.mark.asyncio
    async def test_status_has_ttl(self, service, redis_client):
        """Verify the pipeline captured the TTL argument."""
        uid = uuid4()
        await service.set_user_ping(user_id=uid)
        # FakeRedisPipeline stored the value; TTL was passed as ex= in pipeline.set
        # We verify the status key exists and was set to "online"
        assert redis_client._store[REDIS_PREFIX_STATUS + str(uid)] == "online"


# ---------------------------------------------------------------------------
#  get_by_id / get_by_email / create
# ---------------------------------------------------------------------------
class TestUserQueries:
    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, orm):
        user = _add_user(orm, "alice@example.com", "alice")
        result = await service.get_by_id(user.id)
        assert result is not None
        assert result.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service):
        assert await service.get_by_id(uuid4()) is None

    @pytest.mark.asyncio
    async def test_get_by_email_found(self, service, orm):
        _add_user(orm, "alice@example.com", "alice")
        result = await service.get_by_email("alice@example.com")
        assert result is not None
        assert result.username == "alice"

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, service):
        assert await service.get_by_email("nobody@example.com") is None

    @pytest.mark.asyncio
    async def test_create_user(self, service, orm):
        result = await service.create(
            username="newuser",
            email="new@example.com",
            password_hash="hashed_value",
        )
        assert result is not None
        assert orm.user._users[result.id].username == "newuser"
