"""
This module defines the protocol for message services.
"""

from abc import abstractmethod
from uuid import UUID
from typing import Optional, Protocol, Sequence


class MessageServiceMeta(Protocol):
    """
    Protocol for API services.
    """

    @abstractmethod
    async def get_all(
        self,
        q: str | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Sequence["Message"]:  # type: ignore[return-value]
        """
        Retrieving all messages with filters and limits.

        :param q: Optional query string for filtering.
        :param skip: The number of messages to skip.
        :param limit: The maximum number of messages to retrieve.
        :return: A sequence of messages.
        """
        ...

    @abstractmethod
    async def get_by_id(self, message_id: int) -> Optional["Message"]:  # type: ignore[return-value]
        """
        Retrieve a message by its ID.

        :param message_id: The ID of the message.
        :return: The message if found, otherwise None.
        """
        ...

    @abstractmethod
    async def create(
        self,
        sender_id: UUID,
        content: str,
        recipient_id: UUID,
    ) -> "Message":  # type: ignore[return-value]
        """
        Create a new message.

        :param sender_id: The ID of the sender.
        :param content: The content of the message.
        :param recipient_id: The ID of the recipient.
        :return: The created message.
        """
        ...

    @abstractmethod
    async def get_messages_between_users(
        self,
        recipient_id: UUID,
        sender_id: UUID,
        limit: int = 10,
        before_id: UUID | None = None,  # Скролл вверх по истории
    ) -> Sequence["Message"]:  # type: ignore[return-value]
        """
        Retrieve messages between two users.

        :param recipient_id: The ID of the recipient.
        :param sender_id: The ID of the sender.
        :param limit: The maximum number of messages to retrieve.
        :param before_id: The ID of the last message retrieved.
        :return: A sequence of messages.
        """
        ...
