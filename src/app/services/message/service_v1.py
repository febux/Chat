"""
Message service implementation.
"""

from typing import Optional, Sequence
from uuid import UUID

from src.core.logger.logger_factory import logger_bind
from src.database.sqlalchemy.orm_manager import RepositoryManagerMeta


class MessageService:
    """
    A service class for handling message operations.
    """

    def __init__(
        self,
        orm_manager: RepositoryManagerMeta,
    ):
        self.orm_manager = orm_manager
        self.logger = logger_bind("MessageService")

        self.message_repo = self.orm_manager.message

    async def get_all(
        self,
        q: str | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Sequence["Message"]:  # type: ignore[return-value]
        """
        Retrieving all currencies with filters and limits.

        :param q: Optional query string for filtering.
        :param skip: The number of currencies to skip.
        :param limit: The maximum number of currencies to retrieve.
        :return: A sequence of currencies.
        """
        result = await self.message_repo.get_all(
            q=q,
            skip=skip,
            limit=limit,
        )
        return [message.to_dict() for message in result]

    async def get_by_id(self, message_id: int) -> Optional["Message"]:  # type: ignore[return-value]
        """
        Retrieve a message by its ID.

        :param message_id: The ID of the message.
        :return: The message with the specified ID, or None if not found.
        """
        result = await self.message_repo.read_one(id=message_id)
        return result.to_dict() if result else None

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
        async with self.orm_manager.transaction():
            return await self.message_repo.create(
                sender_id=sender_id,
                content=content,
                recipient_id=recipient_id,
            )

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
        return await self.message_repo.get_messages_between_users(
            recipient_id=recipient_id,
            sender_id=sender_id,
            limit=limit,
            before_id=before_id,
        )