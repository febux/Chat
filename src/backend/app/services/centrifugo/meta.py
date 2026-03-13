"""
This module defines the protocol for Centrifugo services.
"""

from abc import abstractmethod
from typing import Protocol
from uuid import UUID


class CentrifugoServiceMeta(Protocol):
    """
    Protocol for API services.
    """

    @abstractmethod
    async def create_centrifugo_token(
        self,
        user_id: UUID,
    ) -> str:
        """
        Create a Centrifugo token for a given user ID.

        :param user_id: The ID of the user.
        :return: The Centrifugo token.
        """
        ...

    @abstractmethod
    async def publish_to_channel(
        self,
        channel_id: UUID,
        message: "Message",     # type: ignore[arg-value]
    ) -> None:
        """
        Publish a payload to a specific channel.

        :param channel_id: The ID of the channel.
        :param message: The payload to be published.
        :return: None
        """
        ...