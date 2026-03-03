import uuid
from datetime import datetime

from sqlalchemy import DateTime, UUID, ForeignKey, Index
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.models.enums import MemberRole
from src.database import BaseProps


class ChannelMember(BaseProps):
    __tablename__ = "channel_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MemberRole] = mapped_column(
        ENUM(MemberRole, name="channel_member_role"),
        nullable=False,
        default=MemberRole.MEMBER,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # relationships
    channel: Mapped["Channel"] = relationship(  # type: ignore
        "Channel",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(    # type: ignore
        "User",
        back_populates="memberships",
    )

    __table_args__ = (
        # один пользователь не должен дублироваться в одном канале
        Index(
            "uq_channel_members_channel_user",
            "channel_id",
            "user_id",
            unique=True,
        ),
    )
