from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.backend.schemas.base import BaseResponse


class User(BaseResponse):
    id: UUID = Field(..., description="User ID")
    username: str = Field(..., min_length=3, max_length=50, description="Name of the user")
    email: str = Field(..., description="User email")
    status: str | None = Field(None, description="User status")
    last_seen: int | None = Field(None, description="Last seen timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
