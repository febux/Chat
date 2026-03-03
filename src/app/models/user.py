from datetime import datetime

from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import BaseProps


class User(BaseProps):
    __tablename__ = 'users'

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # relationships
    created_channels: Mapped[list["Channel"]] = relationship(       # type: ignore
        "Channel",
        back_populates="creator",
        cascade="all, delete-orphan",
        foreign_keys="Channel.created_by",
    )
    memberships: Mapped[list["ChannelMember"]] = relationship(       # type: ignore
        "ChannelMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["Message"]] = relationship(       # type: ignore
        "Message",
        back_populates="sender",
    )