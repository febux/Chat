from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.backend.schemas.base import BaseSnakeRequest


class User(BaseSnakeRequest):
    id: UUID = Field(..., description="Идентификатор пользователя")
    username: str = Field(..., min_length=3, max_length=50, description="Имя, от 3 до 50 символов")
    email: str = Field(..., description="Электронная почта")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата последнего изменения")
