import uuid
from datetime import datetime

from sqlalchemy import DateTime, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.enums import ChannelType
from src.database import BaseProps


class Channel(BaseProps):
    __tablename__ = "channels"

    type: Mapped[ChannelType] = mapped_column(
        ENUM(ChannelType, name="channel_type"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,  # для direct может быть NULL
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # relationships
    creator: Mapped["User"] = relationship(     # type: ignore
        "User",
        back_populates="created_channels",
        foreign_keys=[created_by],
    )
    members: Mapped[list["ChannelMember"]] = relationship(      # type: ignore
        "ChannelMember",
        back_populates="channel",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["Message"]] = relationship(     # type: ignore
        "Message",
        back_populates="channel",
        cascade="all, delete-orphan",
    )
