"""
Backend test fixtures: fakes for Redis, ORM repositories, and user service.

Provides:
  - FakeRedisPipeline / FakeRedis     — in-memory async Redis mock
  - FakeUserRepo / FakeUserContactRepo — in-memory repository mocks returning SimpleNamespace
  - FakeOrmManager                    — minimal ORM manager with transaction()
  - FakeUserService                   — stub implementing UserServiceMeta
  - make_app()                        — minimal FastAPI app with routers + overrides
  - client / auth_client fixtures     — Starlette TestClient
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Sequence
from uuid import UUID, uuid4

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from src.backend.app.api.admin.v1.users.routes import \
    router as admin_users_router
from src.backend.app.api.admin.v2.maintenance.routes import \
    router as admin_maintenance_router
from src.backend.app.api.public.v1.base.routes import router as base_router
from src.backend.app.api.public.v1.centrifugo.routes import \
    router as centrifugo_router
from src.backend.app.api.public.v1.channel.routes import \
    router as channel_router
from src.backend.app.api.public.v1.users.routes import router as users_router
from src.backend.app.providers.base.provider_v2 import get_service_api_service
from src.backend.app.providers.centrifugo.provider_v1 import \
    get_centrifugo_api_service
from src.backend.app.providers.channel.provider_v1 import \
    get_channel_api_service
from src.backend.app.providers.user.provider_v1 import get_user_api_service
from src.backend.app.services.centrifugo.service_v1 import CentrifugoService
from src.backend.app.services.channel.service_v1 import ChannelService
from src.backend.app.utils.current_user import get_current_user
from src.backend.schemas.users.user_get import User


# ---------------------------------------------------------------------------
#  In-memory async Redis mock
# ---------------------------------------------------------------------------
class FakeRedisPipeline:
    def __init__(self, store: dict[str, str]) -> None:
        self._store = store
        self._ops: list[tuple[str, ...]] = []

    async def set(self, key: str, value: Any, ex: int | None = None) -> None:
        self._ops.append(("set", key, str(value)))

    async def get(self, key: str) -> None:
        self._ops.append(("get", key))

    async def execute(self) -> list[Any]:
        results: list[Any] = []
        for op in self._ops:
            if op[0] == "set":
                self._store[op[1]] = op[2]
                results.append(True)
            elif op[0] == "get":
                val = self._store.get(op[1])
                results.append(val.encode() if val else None)
        self._ops.clear()
        return results


class FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def pipeline(self) -> FakeRedisPipeline:
        return FakeRedisPipeline(self._store)


# ---------------------------------------------------------------------------
#  In-memory repository mocks — return SimpleNamespace (attribute-access)
# ---------------------------------------------------------------------------
class FakeUserRepo:
    """Returns SimpleNamespace objects so the real UserService (which uses
    .id / .email / .password_hash attribute access) works correctly."""

    def __init__(self) -> None:
        self._users: dict[UUID, SimpleNamespace] = {}

    def _add(self, **fields) -> SimpleNamespace:
        uid = fields.get("id", uuid4())
        record = SimpleNamespace(
            id=uid,
            created_at=fields.get("created_at", datetime.now(timezone.utc)),
            updated_at=fields.get("updated_at", datetime.now(timezone.utc)),
            is_active=True,
            deleted_at=None,
            **{k: v for k, v in fields.items() if k not in ("id", "created_at", "updated_at")},
        )
        self._users[uid] = record
        return record

    async def get_all(self, q: str | None = None, skip: int = 0, limit: int = 10) -> list[SimpleNamespace]:
        results = list(self._users.values())
        if q:
            results = [
                u for u in results
                if q.lower() in getattr(u, "email", "").lower()
                or q.lower() in getattr(u, "username", "").lower()
            ]
        return results[skip : skip + limit] if limit else results[skip:]

    async def read_one(self, **kwargs) -> SimpleNamespace | None:
        for record in self._users.values():
            if all(getattr(record, k, None) == v for k, v in kwargs.items()):
                return record
        return None

    async def get_current_user_contacts(self, user_id: UUID) -> list[SimpleNamespace]:
        return [u for u in self._users.values() if u.id != user_id]

    async def create(self, **fields) -> SimpleNamespace:
        return self._add(**fields)


class FakeUserContactRepo:
    def __init__(self) -> None:
        self._contacts: set[tuple[UUID, UUID]] = set()

    async def read_one(self, **kwargs) -> SimpleNamespace | None:
        pair = (kwargs.get("user_id"), kwargs.get("contact_id"))
        # Check both forward and reverse
        if pair in self._contacts or (pair[1], pair[0]) in self._contacts:
            return SimpleNamespace(user_id=pair[0], contact_id=pair[1])
        return None

    async def create(self, **kwargs) -> SimpleNamespace:
        pair = (kwargs["user_id"], kwargs["contact_id"])
        self._contacts.add(pair)
        return SimpleNamespace(user_id=pair[0], contact_id=pair[1])


class FakeChannelRepo:
    """In-memory channel repository used by channel service tests."""

    def __init__(self) -> None:
        self._channels: list[SimpleNamespace] = []

    async def create(self, **fields) -> SimpleNamespace:
        record = SimpleNamespace(
            id=fields.get("id", uuid4()),
            type=fields.get("type"),
            title=fields.get("title"),
            created_by=fields.get("created_by"),
            created_at=datetime.now(timezone.utc),
        )
        record.to_dict = lambda: {
            "id": str(record.id),
            "type": record.type.value if record.type is not None else None,
            "title": record.title,
            "created_by": str(record.created_by),
            "created_at": record.created_at.isoformat(),
        }
        self._channels.append(record)
        return record


class FakeChannelMemberRepo:
    """In-memory channel member repository used by channel service tests."""

    def __init__(self) -> None:
        self._members: list[SimpleNamespace] = []

    async def bulk_create(self, items: Sequence[dict[str, Any]]) -> list[SimpleNamespace]:
        records = [SimpleNamespace(**item) for item in items]
        self._members.extend(records)
        return records

    async def read_one(self, **kwargs) -> SimpleNamespace | None:
        channel_id = kwargs.get("channel_id")
        user_id = kwargs.get("user_id")
        for member in self._members:
            if str(member.channel_id) == str(channel_id) and str(member.user_id) == str(user_id):
                return member
        return None

    async def get_all_channel_members_by_channel_id(self, channel_id: UUID) -> list[SimpleNamespace]:
        return [m for m in self._members if str(m.channel_id) == str(channel_id)]


class FakeOrmManager:
    def __init__(self) -> None:
        self.user = FakeUserRepo()
        self.user_contact = FakeUserContactRepo()
        self.channel = FakeChannelRepo()
        self.channel_member = FakeChannelMemberRepo()

    @asynccontextmanager
    async def transaction(self):
        yield


# ---------------------------------------------------------------------------
#  FakeUserService — stub for API-layer tests
# ---------------------------------------------------------------------------
class FakeUserService:
    """Lightweight stub implementing the UserServiceMeta protocol."""

    def __init__(self) -> None:
        self._users: dict[str, dict] = {}
        self.contacts_created: list[tuple[UUID, UUID]] = []
        self.ping_called: list[UUID] = []

    def _make_user(self, user_id: UUID | None = None, **fields) -> User:
        uid = user_id or fields.get("id", uuid4())
        now = datetime.now(timezone.utc)
        return User(
            id=uid,
            username=fields.get("username", "testuser"),
            email=fields.get("email", "test@example.com"),
            status=fields.get("status"),
            last_seen=fields.get("last_seen"),
            is_admin=fields.get("is_admin", False),
            created_at=fields.get("created_at", now),
            updated_at=fields.get("updated_at", now),
        )

    async def get_all(self, q: str | None = None, skip: int = 0, limit: int = 10) -> Sequence[User]:
        return [self._make_user(**u) for u in list(self._users.values())[skip : skip + limit]]

    async def get_current_user_contacts(self, user_id: UUID) -> Sequence[User]:
        return [self._make_user(**u) for u in self._users.values()]

    async def get_by_id(self, user_id: UUID) -> User | None:
        for u in self._users.values():
            if str(u.get("id")) == str(user_id):
                return self._make_user(**u)
        return None

    async def get_by_email(self, email: str) -> User | None:
        for u in self._users.values():
            if u.get("email") == email:
                return self._make_user(**u)
        return None

    async def create(self, username: str, email: str, password_hash: str, **kwargs) -> User:
        uid = uuid4()
        self._users[str(uid)] = {"id": uid, "username": username, "email": email, "password_hash": password_hash}
        return self._make_user(id=uid, username=username, email=email)

    async def contact_user(self, user_id: UUID, contact_email: str) -> bool:
        user = await self.get_by_email(contact_email)
        if not user or user.id == user_id:
            return False
        pair = (user_id, user.id)
        if pair in self.contacts_created:
            return False
        self.contacts_created.append(pair)
        return True

    async def authenticate_user(self, email: str, password: str) -> User | None:
        from src.backend.utils.password import verify_password

        user = await self.get_by_email(email)
        if not user:
            return None
        stored = self._users.get(str(user.id), {})
        if not await verify_password(password, stored.get("password_hash", "")):
            return None
        return user

    async def set_user_ping(self, user_id: UUID) -> None:
        self.ping_called.append(user_id)


class FakeBaseApiService:
    """Lightweight stub implementing BaseApiServiceMeta for admin v2 tests."""

    async def healthcheck(self, request) -> dict:
        return {"status": "healthy"}

    async def system_metrics(self, request) -> dict:
        return {"metrics": "ok"}


# ---------------------------------------------------------------------------
#  Test data helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_user_id() -> UUID:
    return UUID("12345678-1234-1234-1234-123456789abc")


@pytest.fixture
def sample_user(sample_user_id: UUID) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=sample_user_id,
        username="alice",
        email="alice@example.com",
        status=None,
        last_seen=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_admin_user(sample_user_id: UUID) -> User:
    """Authenticated user with admin privileges for admin route tests."""
    now = datetime.now(timezone.utc)
    return User(
        id=sample_user_id,
        username="admin",
        email="admin@example.com",
        status=None,
        last_seen=None,
        is_admin=True,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
#  Test app factory with dependency overrides
# ---------------------------------------------------------------------------
def _build_test_app(
    fake_service: FakeUserService,
    current_user: User | None = None,
    channel_orm_manager: FakeOrmManager | None = None,
    centrifugo_orm_manager: FakeOrmManager | None = None,
) -> FastAPI:
    from src.backend.app.handlers.exception_handlers import \
        add_exceptions_handlers

    app = FastAPI()
    api = APIRouter(prefix="/api/v1")
    api.include_router(base_router)
    api.include_router(users_router, prefix="/users")
    api.include_router(centrifugo_router, prefix="/centrifugo")
    if channel_orm_manager is not None:
        api.include_router(channel_router, prefix="/channels")
    app.include_router(api)

    # Register admin API routes under the same test app.
    app.include_router(admin_users_router, prefix="/admin/api/v1/users")
    app.include_router(admin_maintenance_router, prefix="/admin/api/v2")

    # Register exception handlers so ClientAPIException → proper HTTP status
    add_exceptions_handlers(app)

    app.dependency_overrides[get_user_api_service] = lambda: fake_service
    app.dependency_overrides[get_service_api_service] = lambda: FakeBaseApiService()

    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user

    if channel_orm_manager is not None:
        app.dependency_overrides[get_channel_api_service] = lambda: ChannelService(channel_orm_manager)

    if centrifugo_orm_manager is not None:
        app.dependency_overrides[get_centrifugo_api_service] = lambda: CentrifugoService(centrifugo_orm_manager)

    return app


@pytest.fixture
def fake_service() -> FakeUserService:
    return FakeUserService()


@pytest.fixture
def client(fake_service: FakeUserService, sample_user: User) -> TestClient:
    """TestClient with auth dependency overridden (all routes appear authenticated)."""
    app = _build_test_app(fake_service, current_user=sample_user)
    return TestClient(app)


@pytest.fixture
def unauth_client(fake_service: FakeUserService) -> TestClient:
    """TestClient WITHOUT get_current_user override — tests auth-guard behaviour."""
    app = _build_test_app(fake_service, current_user=None)
    return TestClient(app)


@pytest.fixture
def admin_client(fake_service: FakeUserService, sample_admin_user: User) -> TestClient:
    """TestClient with an admin user as the authenticated current user."""
    app = _build_test_app(fake_service, current_user=sample_admin_user)
    return TestClient(app)


@pytest.fixture
def centrifugo_orm() -> FakeOrmManager:
    """Fake ORM manager with channel_member populated for centrifugo tests."""
    return FakeOrmManager()


@pytest.fixture
def centrifugo_service(centrifugo_orm: FakeOrmManager) -> CentrifugoService:
    """Real CentrifugoService backed by the fake ORM manager."""
    return CentrifugoService(centrifugo_orm)


@pytest.fixture
def centrifugo_client(
    fake_service: FakeUserService,
    sample_user: User,
    centrifugo_orm: FakeOrmManager,
) -> TestClient:
    """Authenticated TestClient wired to the real CentrifugoService + fake repos."""
    app = _build_test_app(
        fake_service,
        current_user=sample_user,
        centrifugo_orm_manager=centrifugo_orm,
    )
    return TestClient(app, raise_server_exceptions=False)
