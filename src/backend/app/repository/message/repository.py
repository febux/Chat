"""
Message repository module for CRUD operations on Message model.
"""
from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, desc, or_, select

from src.backend.app.models import Message
from src.backend.app.repository.meta import AbstractRepository


class MessageRepository(AbstractRepository[Message]):
    """
    Message repository for CRUD operations on Message model.
    """

    _model = Message

    async def get_messages_between_users(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        limit: int = 30,
        before_id: UUID | None = None,  # Последний ID с фронта (для скролла вверх)
    ) -> Sequence[Message]:
        """
        Retrieve messages between two users with cursor-based pagination.

        Results are returned oldest-first. The first page returns the most recent
        ``limit`` messages; subsequent pages return the ``limit`` messages older
        than ``before_id``. Uses a single range query per page (no COUNT, no OFFSET).

        :param sender_id: Sender ID
        :param recipient_id: Recipient ID
        :param limit: Limit of messages (1-100)
        :param before_id: ID of the oldest message currently shown (for scrolling up)
        :return: Sequence of messages, oldest-first
        """
        base_where = or_(
            and_(
                self.model.sender_id == sender_id,
                self.model.channel_id == recipient_id,
            ),
            and_(
                self.model.sender_id == recipient_id,
                self.model.channel_id == sender_id,
            ),
        )

        query = select(self.model).where(base_where)

        if before_id:
            before_msg = await self.read_one(id=before_id)
            if before_msg is None:
                # Cursor points to a message that no longer exists; tell the
                # client there is nothing older to load rather than silently
                # returning page one again.
                return []
            query = query.where(
                or_(
                    self.model.created_at < before_msg.created_at,
                    and_(
                        self.model.created_at == before_msg.created_at,
                        self.model.id < before_id,
                    ),
                )
            )

        # Fetch the newest ``limit`` rows of the selected range, then reverse so
        # the caller receives them oldest-first.
        query = query.order_by(
            desc(self.model.created_at),
            desc(self.model.id),
        ).limit(limit)

        result = await self.session.execute(query)
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def get_messages_between_users_paginated(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        limit: int = 30,
        before_id: UUID | None = None,
    ) -> tuple[Sequence[Message], bool]:
        """
        Get messages between two users with cursor-based pagination and return a
        tuple of messages and a flag indicating if there are more messages.

        :param sender_id: ID of sender
        :param recipient_id: ID of recipient
        :param limit: Limit of messages (1-100)
        :param before_id: ID of the last message (for scrolling up)
        :return: (messages, has_more)
        """
        messages = await self.get_messages_between_users(
            sender_id=sender_id,
            recipient_id=recipient_id,
            limit=limit,
            before_id=before_id,
        )

        has_more = len(messages) == limit

        return messages, has_more

    async def get_messages_for_channel(
        self,
        channel_id: UUID,
        limit: int = 30,
        before_id: UUID | None = None,
    ) -> Sequence[Message]:
        """
        Retrieve messages for a specific channel with cursor-based pagination.

        Results are returned oldest-first. The first page returns the most recent
        ``limit`` messages; subsequent pages return the ``limit`` messages older
        than ``before_id``. Uses a single range query per page (no COUNT, no OFFSET).

        :param channel_id: ID of the channel
        :param limit: Limit of messages (1-100)
        :param before_id: ID of the oldest message currently shown (for scrolling up)
        :return: Sequence of messages, oldest-first
        """
        base_where = self.model.channel_id == channel_id
        query = select(self.model).where(base_where)

        if before_id:
            before_msg = await self.read_one(id=before_id)
            if before_msg is None:
                return []
            query = query.where(
                or_(
                    self.model.created_at < before_msg.created_at,
                    and_(
                        self.model.created_at == before_msg.created_at,
                        self.model.id < before_id,
                    ),
                )
            )

        query = query.order_by(
            desc(self.model.created_at),
            desc(self.model.id),
        ).limit(limit)

        result = await self.session.execute(query)
        messages = list(result.scalars().all())
        messages.reverse()
        return messages


repository = MessageRepository
