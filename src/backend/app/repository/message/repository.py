"""
Message repository module for CRUD operations on Message model.
"""
from typing import Sequence
from uuid import UUID

from sqlalchemy import select, or_, and_, asc, func

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

        :param sender_id: Sender ID
        :param recipient_id: Recipient ID
        :param limit: Limit of messages (1-100)
        :param before_id: ID of the last message (for scrolling up)
        :return: Sequence of messages
        """
        base_where = or_(
            and_(
                self.model.sender_id == sender_id,
                self.model.channel_id == recipient_id,
            ),
            and_(
                self.model.sender_id == recipient_id,
                self.model.channel_id == sender_id,
            )
        )

        if before_id:
            before_msg = await self.read_one(id=before_id)
            if before_msg:
                query = select(self.model).where(
                    base_where,
                    or_(
                        self.model.created_at < before_msg.created_at,
                        and_(
                            self.model.created_at == before_msg.created_at,
                            self.model.id < before_id
                        )
                    )
                )
            else:
                # fallback
                query = select(self.model).where(base_where)
        else:
            count_query = select(func.count()).where(base_where)
            total_count = await self.session.scalar(count_query)
            offset = max(0, total_count - limit)

            boundary_query = select(self.model).where(
                base_where
            ).order_by(
                asc(self.model.created_at),
                asc(self.model.id)
            ).offset(offset).limit(1)

            boundary_msg = await self.session.scalar(boundary_query)

            if boundary_msg:
                query = select(self.model).where(
                    base_where,
                    or_(
                        self.model.created_at > boundary_msg.created_at,
                        and_(
                            self.model.created_at == boundary_msg.created_at,
                            self.model.id >= boundary_msg.id
                        )
                    )
                )
            else:
                query = select(self.model).where(base_where)

        query = query.order_by(
            asc(self.model.created_at),
            asc(self.model.id)
        ).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_messages_between_users_paginated(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        limit: int = 30,
        before_id: UUID | None = None,
    ) -> tuple[Sequence[Message], bool]:
        """
        Get messages between two users with cursor-based pagination and return a tuple of messages and a flag indicating if there are more messages.

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

        :param channel_id: ID of the channel
        :param limit: Limit of messages (1-100)
        :param before_id: ID of the last message (for scrolling up)
        :return: Sequence of messages
        """
        base_where = self.model.channel_id == channel_id
        if before_id:
            before_msg = await self.read_one(id=before_id)
            if before_msg:
                query = select(self.model).where(
                    base_where,
                    or_(
                        self.model.created_at < before_msg.created_at,
                        and_(
                            self.model.created_at == before_msg.created_at,
                            self.model.id < before_id
                        )
                    )
                )
            else:
                # fallback
                query = select(self.model).where(base_where)
        else:
            count_query = select(func.count()).where(base_where)
            total_count = await self.session.scalar(count_query)
            offset = max(0, total_count - limit)

            boundary_query = select(self.model).where(
                base_where
            ).order_by(
                asc(self.model.created_at),
                asc(self.model.id)
            ).offset(offset).limit(1)

            boundary_msg = await self.session.scalar(boundary_query)

            if boundary_msg:
                query = select(self.model).where(
                    base_where,
                    or_(
                        self.model.created_at > boundary_msg.created_at,
                        and_(
                            self.model.created_at == boundary_msg.created_at,
                            self.model.id >= boundary_msg.id
                        )
                    )
                )
            else:
                query = select(self.model).where(base_where)

        query = query.order_by(
            asc(self.model.created_at),
            asc(self.model.id)
        ).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()



repository = MessageRepository
