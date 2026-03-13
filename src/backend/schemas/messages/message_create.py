from uuid import UUID

from pydantic import BaseModel, Field


class ChannelMessageCreate(BaseModel):
    channel_id: UUID = Field(..., description="ID канала")
    content: str = Field(..., description="Содержимое сообщения")
