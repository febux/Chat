"""
This module defines the protocol for Channel services.
"""

from abc import abstractmethod
from typing import Protocol, Optional, Sequence
from uuid import UUID

from src.backend.app.models.enums import ChannelType


class ChannelServiceMeta(Protocol):
    """
    Protocol for API services.
    """

    @abstractmethod
    async def get_user_channels(
        self,
        user_id: UUID,
    ) -> Sequence["Channel"]:  # type: ignore[return-value]
        """
        Retrieve all channels associated with the given user.

        :param user_id: ID of the user.
        :return: A list of channels.
        """
        ...

    @abstractmethod
    async def find_channel_between_users(
        self,
        user_ids: Sequence[UUID],
    ) -> Optional["Channel"]:  # type: ignore[return-value]
        """
        Find a channel between two or more users.

        :param user_ids: IDs of the users.
        :return: The channel if found, otherwise None.
        """
        ...

    @abstractmethod
    async def create(
        self,
        channel_type: ChannelType,
        title: Optional[str],
        created_by: UUID,
    ) -> "Channel":  # type: ignore[return-value]
        """
        Create a new channel.

        :param channel_type: Type of the channel.
        :param title: Title of the channel.
        :param created_by: ID of the user who created the channel.
        :return: The created channel.
        """
        ...

    @abstractmethod
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
        ...