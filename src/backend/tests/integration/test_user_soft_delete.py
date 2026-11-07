"""
Integration tests for soft-delete user unique indexes.

These tests hit a real SQLite database so they can verify that:
  * partial unique indexes allow reusing a deleted user's email/username
  * active users still cannot share email/username
  * the Alembic migration applies correctly on SQLite
  * PostgreSQL-compatible partial-index SQL is generated
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from io import StringIO

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import URL
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tests.conftest import FakeRedis

from src.backend.app.models import User
from src.backend.app.services.user.service_v1 import UserService
from src.backend.database.sqlalchemy.orm_manager.manager import \
    OrmRepositoryManager
from src.backend.database.sqlalchemy.session_manager import sessionmanager
from src.backend.utils.password import hash_password_sync


@pytest.fixture
def sqlite_file(tmp_path):
    """Path to a fresh SQLite database file."""
    return tmp_path / "soft_delete_test.db"


@pytest.fixture
def sqlite_url(sqlite_file):
    """Async SQLite URL for a fresh database file."""
    return f"sqlite+aiosqlite:///{sqlite_file}"


@pytest.fixture
def sync_sqlite_url(sqlite_file):
    """Sync SQLite URL for the same database file."""
    return f"sqlite:///{sqlite_file}"


def _patch_sessionmanager_url(url_obj: URL):
    """Replace the global sessionmanager URL used by migrations/env.py."""
    sessionmanager._db_url = url_obj


def _restore_sessionmanager_url(original_url):
    """Restore the original sessionmanager URL."""
    sessionmanager._db_url = original_url


# ---------------------------------------------------------------------------
#  Schema / SQL generation tests
# ---------------------------------------------------------------------------
def test_partial_unique_index_sql_includes_deleted_at_filter():
    """The model's partial indexes compile to SQL with the active-user filter
    for both PostgreSQL and SQLite."""
    email_index = next(idx for idx in User.__table__.indexes if idx.name == "ix_users_email")
    username_index = next(idx for idx in User.__table__.indexes if idx.name == "ix_users_username")

    pg_sql = str(sa.schema.CreateIndex(email_index).compile(dialect=postgresql.dialect()))
    sqlite_sql = str(sa.schema.CreateIndex(email_index).compile(dialect=sqlite.dialect()))

    assert "deleted_at IS NULL" in pg_sql
    assert "deleted_at IS NULL" in sqlite_sql

    pg_sql_user = str(sa.schema.CreateIndex(username_index).compile(dialect=postgresql.dialect()))
    sqlite_sql_user = str(sa.schema.CreateIndex(username_index).compile(dialect=sqlite.dialect()))

    assert "deleted_at IS NULL" in pg_sql_user
    assert "deleted_at IS NULL" in sqlite_sql_user


def test_new_migration_generates_postgresql_partial_index_sql():
    """Running Alembic in offline (sql) mode for PostgreSQL produces the
    partial unique index clauses introduced by the new migration."""
    cfg = Config()
    cfg.set_main_option("script_location", "migrations")
    cfg.set_main_option(
        "sqlalchemy.url",
        "postgresql+asyncpg://user:password@localhost:5432/public",
    )

    old_stdout = sys.stdout
    sys.stdout = buffer = StringIO()
    try:
        command.upgrade(cfg, "head", sql=True)
    finally:
        sys.stdout = old_stdout

    sql = buffer.getvalue()
    # The new migration must add the deleted_at column and create partial indexes.
    assert "ADD COLUMN deleted_at" in sql or "deleted_at" in sql
    assert re.search(
        r"CREATE\s+UNIQUE\s+INDEX\s+ix_users_email\s+ON\s+users\s+\(email\).*WHERE\s+deleted_at\s+IS\s+NULL",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(
        r"CREATE\s+UNIQUE\s+INDEX\s+ix_users_username\s+ON\s+users\s+\(username\).*WHERE\s+deleted_at\s+IS\s+NULL",
        sql,
        re.IGNORECASE | re.DOTALL,
    )


# ---------------------------------------------------------------------------
#  Migration application on SQLite
# ---------------------------------------------------------------------------
def test_migration_applies_to_sqlite(sqlite_url, sync_sqlite_url):
    """Starting from the initial migration state, the new migration adds the
    deleted_at column and replaces the full unique indexes with partial ones."""
    db_path = sqlite_url.split("///")[-1]
    url_obj = URL.create("sqlite+aiosqlite", database=db_path)

    # Build the pre-migration users table directly with a sync engine so we can
    # exercise only the new migration without requiring the full initial schema
    # (which uses PostgreSQL-specific types such as JSONB).
    sync_engine = sa.create_engine(sync_sqlite_url)
    with sync_engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE users (
                    id BLOB PRIMARY KEY NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    username VARCHAR(64) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    last_login_at TIMESTAMP,
                    is_active BOOLEAN NOT NULL,
                    is_admin BOOLEAN NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(sa.text("CREATE UNIQUE INDEX ix_users_email ON users(email)"))
        conn.execute(sa.text("CREATE UNIQUE INDEX ix_users_username ON users(username)"))
        conn.execute(
            sa.text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO alembic_version (version_num) VALUES ('7f3a9c2e1b4d')"
            )
        )

    original_url = sessionmanager._db_url
    _patch_sessionmanager_url(url_obj)
    cfg = Config()
    cfg.set_main_option("script_location", "migrations")
    cfg.set_main_option("sqlalchemy.url", sqlite_url)

    try:
        command.upgrade(cfg, "head")
    finally:
        _restore_sessionmanager_url(original_url)

    with sync_engine.connect() as conn:
        # deleted_at column was added
        columns = {col[1]: col for col in conn.execute(sa.text("PRAGMA table_info(users)")).fetchall()}
        assert "deleted_at" in columns

        # Indexes are partial and unique
        rows = conn.execute(
            sa.text("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='users'")
        ).fetchall()
        index_sql = {name: sql for name, sql in rows}
        assert "deleted_at IS NULL" in index_sql["ix_users_email"]
        assert "deleted_at IS NULL" in index_sql["ix_users_username"]
        assert "UNIQUE" in index_sql["ix_users_email"]
        assert "UNIQUE" in index_sql["ix_users_username"]


# ---------------------------------------------------------------------------
#  Functional regression test against a real SQLite database
# ---------------------------------------------------------------------------
@pytest.fixture
async def sqlite_service(sqlite_url):
    """Create the users table from the updated model and yield a UserService
    backed by a real SQLite database."""
    engine = create_async_engine(sqlite_url)
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        orm = OrmRepositoryManager(session)
        service = UserService(orm_manager=orm, redis_client=FakeRedis())
        yield service, orm

    await engine.dispose()


@pytest.mark.asyncio
async def test_soft_deleted_user_can_be_reregistered(sqlite_service):
    """After a user is soft-deleted, a new account with the same username and
    email can be created."""
    service, orm = sqlite_service

    first = await service.create(
        username="alice",
        email="alice@example.com",
        password_hash="first-hash",
    )
    assert first is not None

    # Soft-delete the first user directly.
    user_row = await orm.user.read_one(id=first.id)
    user_row.deleted_at = datetime.now(timezone.utc)
    await orm.session.commit()

    # The service no longer sees the deleted user by email or id.
    assert await service.get_by_email("alice@example.com") is None
    assert await service.get_by_id(first.id) is None

    # Re-registration with the same email/username succeeds.
    second = await service.create(
        username="alice",
        email="alice@example.com",
        password_hash="second-hash",
    )
    assert second.id != first.id
    assert second.email == "alice@example.com"
    assert second.username == "alice"


@pytest.mark.asyncio
async def test_active_users_still_have_unique_email_and_username(sqlite_service):
    """An active user still blocks another active account with the same
    username or email."""
    service, _orm = sqlite_service

    await service.create(
        username="alice",
        email="alice@example.com",
        password_hash="hash",
    )

    with pytest.raises(IntegrityError):
        await service.create(
            username="alice",
            email="other@example.com",
            password_hash="hash2",
        )

    with pytest.raises(IntegrityError):
        await service.create(
            username="other",
            email="alice@example.com",
            password_hash="hash3",
        )


@pytest.mark.asyncio
async def test_deleted_user_cannot_authenticate(sqlite_service):
    """A soft-deleted user cannot log in even with the right password."""
    service, orm = sqlite_service

    password = "SecretPass123"
    user = await service.create(
        username="alice",
        email="alice@example.com",
        password_hash=hash_password_sync(password),
    )

    assert await service.authenticate_user("alice@example.com", password) is not None

    user_row = await orm.user.read_one(id=user.id)
    user_row.deleted_at = datetime.now(timezone.utc)
    await orm.session.commit()

    assert await service.authenticate_user("alice@example.com", password) is None
