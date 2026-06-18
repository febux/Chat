import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql.base import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.database import BaseProps


class UserContact(BaseProps):
    __tablename__ = "user_contacts"
    __table_args__ = (
        UniqueConstraint("user_id", "contact_id", name="uq_user_contacts_user_id_contact_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
