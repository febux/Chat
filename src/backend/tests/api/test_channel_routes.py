"""
API-layer tests for the channel creation route.

These tests exercise the real route code together with the real ChannelService
backed by in-memory repository fakes, so no database is required.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from starlette.testclient import TestClient
from tests.conftest import FakeOrmManager, FakeUserService, _build_test_app

from src.backend.app.models.enums import MemberRole
from src.backend.schemas.users.user_get import User


def _seed_client(current_user: User, *extra_user_ids: UUID) -> tuple[TestClient, FakeOrmManager]:
    orm = FakeOrmManager()
    orm.user._add(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        password_hash="x",
    )
    for extra_id in extra_user_ids:
        orm.user._add(
            id=extra_id,
            username=f"user-{extra_id}",
            email=f"{extra_id}@example.com",
            password_hash="x",
        )
    app = _build_test_app(
        FakeUserService(),
        current_user=current_user,
        channel_orm_manager=orm,
    )
    return TestClient(app, raise_server_exceptions=False), orm


class TestCreateChannel:
    def test_creator_becomes_admin_when_not_in_members(self, sample_user: User):
        other_id = uuid4()
        client, orm = _seed_client(sample_user, other_id)

        resp = client.post(
            "/api/v1/channels",
            json={"channel_type": "group", "title": "admins-group", "members": [str(other_id)]},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["created_by"] == str(sample_user.id)

        roles = {str(m.user_id): m.role for m in orm.channel_member._members}
        assert roles[str(sample_user.id)] == MemberRole.ADMIN
        assert roles[str(other_id)] == MemberRole.MEMBER

    def test_unknown_member_returns_400(self, sample_user: User):
        client, _ = _seed_client(sample_user)
        unknown_id = uuid4()

        resp = client.post(
            "/api/v1/channels",
            json={"channel_type": "group", "title": "bad-group", "members": [str(unknown_id)]},
        )

        assert resp.status_code == 400
        body = resp.json()
        assert str(unknown_id) in body["detail"][0]["msg"]

    def test_creator_in_members_becomes_admin(self, sample_user: User):
        other_id = uuid4()
        client, orm = _seed_client(sample_user, other_id)

        resp = client.post(
            "/api/v1/channels",
            json={
                "channel_type": "group",
                "title": "group",
                "members": [str(sample_user.id), str(other_id)],
            },
        )

        assert resp.status_code == 201
        roles = {str(m.user_id): m.role for m in orm.channel_member._members}
        assert roles[str(sample_user.id)] == MemberRole.ADMIN
        assert roles[str(other_id)] == MemberRole.MEMBER

    def test_empty_members_still_creates_admin_creator(self, sample_user: User):
        client, orm = _seed_client(sample_user)

        resp = client.post(
            "/api/v1/channels",
            json={"channel_type": "group", "title": "solo", "members": []},
        )

        assert resp.status_code == 201
        assert len(orm.channel_member._members) == 1
        assert orm.channel_member._members[0].user_id == sample_user.id
        assert orm.channel_member._members[0].role == MemberRole.ADMIN
