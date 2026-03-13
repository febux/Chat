from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.backend.app.models.enums import ChannelType


class Channel(BaseModel):
    id: UUID
    type: ChannelType
    title: str | None
    created_by: UUID
    created_at: datetime
