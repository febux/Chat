"""
Channel repository module for CRUD operations on Channel model.
"""
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select

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
        """
        Find the (direct) channel whose exact member set equals ``user_ids``.

        The previous implementation filtered members to the requested users *then*
        counted, so a channel with members {A,B,C} matched a search for {A,B}.
        We now restrict to candidate channels (those containing at least one
        requested user) and require the channel's *total* member count to equal
        ``len(user_ids)``, which guarantees an exact member-set match.

        :param user_ids: IDs of the users.
        :return: The channel if found, otherwise None.
        """
        if not user_ids:
            return None
        num_users = len(user_ids)

        candidate_channels = (
            select(ChannelMember.channel_id)
            .where(ChannelMember.user_id.in_(user_ids))
            .distinct()
            .subquery()
        )

        subq = (
            select(ChannelMember.channel_id)
            .join(
                candidate_channels,
                ChannelMember.channel_id == candidate_channels.c.channel_id,
            )
            .group_by(ChannelMember.channel_id)
            .having(func.count(ChannelMember.user_id) == num_users)
            .subquery()
        )

        query = select(self.model).where(self.model.id.in_(select(subq.c.channel_id)))

        result = await self.session.execute(query)
        return result.scalars().first()


repository = ChannelRepository
