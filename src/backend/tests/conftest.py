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
from typing import Annotated, Any, Sequence
from uuid import UUID, uuid4

import pytest
from fastapi import APIRouter, Depends, FastAPI
from starlette.testclient import TestClient

from src.backend.app.api.public.v1.base.routes import router as base_router
from src.backend.app.api.public.v1.users.routes import router as users_router
from src.backend.app.providers.user.provider_v1 import get_user_api_service
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


class FakeOrmManager:
    def __init__(self) -> None:
        self.user = FakeUserRepo()
        self.user_contact = FakeUserContactRepo()

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


# ---------------------------------------------------------------------------
#  Test app factory with dependency overrides
# ---------------------------------------------------------------------------
def _build_test_app(fake_service: FakeUserService, current_user: User | None = None) -> FastAPI:
    from src.backend.app.handlers.exception_handlers import \
        add_exceptions_handlers

    app = FastAPI()
    api = APIRouter(prefix="/api/v1")
    api.include_router(base_router)
    api.include_router(users_router, prefix="/users")
    app.include_router(api)

    # Register exception handlers so ClientAPIException → proper HTTP status
    add_exceptions_handlers(app)

    app.dependency_overrides[get_user_api_service] = lambda: fake_service

    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user

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
