"""
Channel repository module for CRUD operations on Channel model.
"""
from typing import Sequence
from uuid import UUID

from sqlalchemy import select, func

from src.backend.app.models import Channel, ChannelMember
from src.backend.app.repository.meta import AbstractRepository


class ChannelRepository(AbstractRepository[Channel]):
    """
    Channel repository for CRUD operations on Channel model.
    """

    _model = Channel

    async def get_all_channels_by_user_id(self, user_id: UUID) -> Sequence[Channel]:
        """
        Retrieve all channels associated with a specific user.

        :param user_id: ID of the user.
        :return: A list of channels.
        """
        query = select(
            self.model
        ).join(
            ChannelMember, self.model.id == ChannelMember.channel_id
        ).where(
            ChannelMember.user_id == user_id
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def find_channel_between_users(self, user_ids: Sequence[UUID]):
        num_users = len(user_ids)

        subq = (
            select(ChannelMember.channel_id)
            .where(ChannelMember.user_id.in_(user_ids))
            .group_by(ChannelMember.channel_id)
            .having(func.count(ChannelMember.user_id) == num_users)
            .subquery()
        )

        query = select(self.model).where(self.model.id.in_(select(subq.c.channel_id)))

        result = await self.session.execute(query)
        return result.scalars().first()


repository = ChannelRepository
