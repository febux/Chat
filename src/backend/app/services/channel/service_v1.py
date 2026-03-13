"""
Channel service implementation.
"""

from typing import Optional, Sequence
from uuid import UUID

from src.backend.app.models.enums import ChannelType, MemberRole
from src.backend.core.logger.logger_factory import logger_bind
from src.backend.database.sqlalchemy.orm_manager import RepositoryManagerMeta


class ChannelService:
    """
    A service class for handling Channel operations.
    """

    def __init__(
        self,
        orm_manager: RepositoryManagerMeta,
    ):
        self.orm_manager = orm_manager
        self.logger = logger_bind("ChannelService")

        self.channel_repo = self.orm_manager.channel
        self.channel_member_repo = self.orm_manager.channel_member

    async def get_user_channels(
        self,
        user_id: UUID,
    ) -> Sequence["Channel"]:  # type: ignore[return-value]
        """
        Retrieve all channels associated with the given user.

        :param user_id: ID of the user.
        :return: A list of channels.
        """
        return await self.channel_repo.get_all_channels_by_user_id(user_id)

    async def find_channel_between_users(
        self,
        user_ids: Sequence[UUID],
    ) -> Optional["Channel"]:  # type: ignore[return-value]
        """
        Find a channel between two or more users.

        :param user_ids: IDs of the users.
        :return: The channel if found, otherwise None.
        """
        return await self.channel_repo.find_channel_between_users(user_ids)

    async def create(
        self,
        channel_type: ChannelType,
        title: Optional[str],
        created_by: UUID,
    ) -> "Channel": # type: ignore[return-value]
        """
        Create a new channel.

        :param channel_type: Type of the channel.
        :param title: Title of the channel.
        :param created_by: ID of the user who created the channel.
        :return: The created channel.
        """
        async with self.orm_manager.transaction():
            channel = await self.channel_repo.create(
                type=channel_type,
                title=title,
                created_by=created_by,
            )
            self.logger.info(f"Channel '{channel.id}' created.")
            return channel.to_dict()

    async def create_channel_with_members(
        self,
        channel_type: ChannelType,
        title: Optional[str],
        created_by: UUID,
        members: Sequence[UUID],
    ) -> "Channel":  # type: ignore[return-value]
        """
        Create a new channel with members.

        :param channel_type: Type of the channel.
        :param title: Title of the channel.
        :param created_by: ID of the user who created the channel.
        :param members: IDs of the members in the channel.
        :return: The created channel.
        """
        async with self.orm_manager.transaction():
            channel = await self.channel_repo.create(
                type=channel_type,
                title=title,
                created_by=created_by,
            )
            self.logger.info(f"Channel '{channel.id}' created with members.")
            for member_id in members:
                await self.channel_member_repo.create(
                    channel_id=channel.id,
                    user_id=member_id,
                    role=MemberRole.MEMBER,
                )
            return channel.to_dict()