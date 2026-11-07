from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import BaseProps


class User(BaseProps):
    __tablename__ = 'users'

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    username: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
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
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index(
            'ix_users_email',
            'email',
            unique=True,
            postgresql_where=text('deleted_at IS NULL'),
            sqlite_where=text('deleted_at IS NULL'),
        ),
        Index(
            'ix_users_username',
            'username',
            unique=True,
            postgresql_where=text('deleted_at IS NULL'),
            sqlite_where=text('deleted_at IS NULL'),
        ),
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

    def to_dict(
        self,
        include_created_channels: bool = False,
        include_memberships: bool = False,
        include_messages: bool = False,
    ) -> dict:
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_channels": [ch.to_dict() for ch in self.created_channels] if include_created_channels else None,
            "memberships": [ch.to_dict() for ch in self.memberships] if include_memberships else None,
            "messages": [msg.to_dict() for msg in self.messages] if include_messages else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
