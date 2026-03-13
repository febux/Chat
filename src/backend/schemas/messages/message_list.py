from uuid import UUID

from pydantic import BaseModel, Field

from src.backend.schemas.messages.message_get import Message


class MessageList(BaseModel):
    messages: list[Message] = Field(..., description="Список сообщений")
    has_more: bool = Field(..., description="Есть ли ещё сообщения")
    next_before_id: UUID | None = Field(default=None, description="ID последнего сообщения для скролла вверх")
