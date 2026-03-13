from uuid import UUID

from pydantic import BaseModel, Field

from src.backend.app.models.enums import ChannelType


class ChannelWithMembersCreate(BaseModel):
    channel_type: ChannelType = Field(..., description="Тип канала")
    title: str | None = Field(None, description="Название канала")
    created_by: UUID = Field(..., description="ID создателя канала")
    members: list[UUID] = Field(default_factory=list, description="Список ID участников канала")
