from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Message(BaseModel):
    id: UUID = Field(..., description="Уникальный идентификатор сообщения")
    sender_id: UUID = Field(..., description="ID отправителя сообщения")
    recipient_id: UUID = Field(..., description="ID получателя сообщения")
    content: str = Field(..., description="Содержимое сообщения")
    created_at: datetime = Field(..., description="Дата создания сообщения")
