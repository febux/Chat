import uuid
from datetime import datetime

from sqlalchemy import UUID, ForeignKey, Index, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import BaseProps


class Message(BaseProps):
    __tablename__ = "messages"

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[dict | str] = mapped_column(
        JSONB,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # relationships
    channel: Mapped["Channel"] = relationship(  # type: ignore
        "Channel",
        back_populates="messages",
    )
    sender: Mapped["User"] = relationship(      # type: ignore
        "User",
        back_populates="messages",
    )

    __table_args__ = (
        # индекс для выборки истории по каналу с сортировкой по времени
        Index(
            "ix_messages_channel_created_at_desc",
            "channel_id",
            "created_at",
            postgresql_using="btree",
        ),
    )
