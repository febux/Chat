import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, ForeignKey, Index, column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import BaseProps


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
        # Composite index backing channel history read latest-first. The
        # created_at segment is DESC so it serves ORDER BY created_at DESC,
        # id DESC with a forward scan (and the index name is now truthful).
        Index(
            "ix_messages_channel_created_at_desc",
            column("channel_id"),
            column("created_at").desc(),
            postgresql_using="btree",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "channel_id": str(self.channel_id),
            "sender_id": str(self.sender_id),
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }
