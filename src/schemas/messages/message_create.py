from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    recipient_id: UUID = Field(..., description="ID получателя сообщения")
    content: str = Field(..., description="Содержимое сообщения")
