"""
Unit tests for ChannelService.create_channel_with_members.

Uses the in-memory fakes from tests.conftest so no real database is required.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from tests.conftest import FakeOrmManager

from src.backend.app.models.enums import ChannelType, MemberRole
from src.backend.app.services.channel.service_v1 import ChannelService
from src.backend.common.exceptions.api.client_exception import \
    ClientAPIException


def _add_user(orm: FakeOrmManager, user_id: UUID | None = None, username: str = "user") -> UUID:
    record = orm.user._add(
        id=user_id or uuid4(),
        username=username,
        email=f"{username}@example.com",
        password_hash="x",
    )
    return record.id


@pytest.fixture
def orm() -> FakeOrmManager:
    return FakeOrmManager()


@pytest.fixture
def service(orm: FakeOrmManager) -> ChannelService:
    return ChannelService(orm)


@pytest.mark.asyncio
async def test_creator_added_as_admin_when_not_in_members(service: ChannelService, orm: FakeOrmManager):
    creator_id = _add_user(orm, username="creator")
    other_id = _add_user(orm, username="other")

    result = await service.create_channel_with_members(
        channel_type=ChannelType.GROUP,
        title="test-group",
        created_by=creator_id,
        members=[other_id],
    )

    channel_id = UUID(result["id"])
    members = await orm.channel_member.get_all_channel_members_by_channel_id(channel_id)
    roles = {str(m.user_id): m.role for m in members}

    assert roles[str(creator_id)] == MemberRole.ADMIN
    assert roles[str(other_id)] == MemberRole.MEMBER


@pytest.mark.asyncio
async def test_unknown_member_raises_400_and_does_not_create_channel(
    service: ChannelService, orm: FakeOrmManager
):
    creator_id = _add_user(orm, username="creator")
    unknown_id = uuid4()

    with pytest.raises(ClientAPIException) as exc_info:
        await service.create_channel_with_members(
            channel_type=ChannelType.GROUP,
            title="bad-group",
            created_by=creator_id,
            members=[unknown_id],
        )

    assert exc_info.value.status_code == 400
    assert str(unknown_id) in exc_info.value.detail[0]["msg"]
    assert not orm.channel._channels
    assert not orm.channel_member._members


@pytest.mark.asyncio
async def test_creator_in_members_becomes_admin(service: ChannelService, orm: FakeOrmManager):
    creator_id = _add_user(orm, username="creator")
    other_id = _add_user(orm, username="other")

    result = await service.create_channel_with_members(
        channel_type=ChannelType.GROUP,
        title="group",
        created_by=creator_id,
        members=[creator_id, other_id],
    )

    channel_id = UUID(result["id"])
    members = await orm.channel_member.get_all_channel_members_by_channel_id(channel_id)
    roles = {str(m.user_id): m.role for m in members}

    assert len(roles) == 2
    assert roles[str(creator_id)] == MemberRole.ADMIN
    assert roles[str(other_id)] == MemberRole.MEMBER


@pytest.mark.asyncio
async def test_empty_members_adds_creator_as_admin(service: ChannelService, orm: FakeOrmManager):
    creator_id = _add_user(orm, username="creator")

    result = await service.create_channel_with_members(
        channel_type=ChannelType.GROUP,
        title="solo-group",
        created_by=creator_id,
        members=[],
    )

    channel_id = UUID(result["id"])
    members = await orm.channel_member.get_all_channel_members_by_channel_id(channel_id)
    assert len(members) == 1
    assert members[0].user_id == creator_id
    assert members[0].role == MemberRole.ADMIN


@pytest.mark.asyncio
async def test_multiple_unknown_members_are_all_reported(service: ChannelService, orm: FakeOrmManager):
    creator_id = _add_user(orm, username="creator")
    unknown_one = uuid4()
    unknown_two = uuid4()

    with pytest.raises(ClientAPIException) as exc_info:
        await service.create_channel_with_members(
            channel_type=ChannelType.GROUP,
            title="bad-group",
            created_by=creator_id,
            members=[unknown_one, unknown_two],
        )

    msg = exc_info.value.detail[0]["msg"]
    assert str(unknown_one) in msg
    assert str(unknown_two) in msg
    assert exc_info.value.status_code == 400
