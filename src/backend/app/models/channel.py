import uuid

from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.app.models.enums import ChannelType
from src.backend.database import BaseProps


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

    def to_dict(
        self,
        include_members: bool = False,
        include_messages: bool = False,
    ) -> dict:
        return {
            "id": str(self.id),
            "type": self.type.value,
            "title": self.title,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat(),
            "members": [member.to_dict() for member in self.members] if include_members else None,
            "messages": [message.to_dict() for message in self.messages] if include_messages else None,
        }
