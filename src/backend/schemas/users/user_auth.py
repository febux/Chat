from pydantic import Field

from src.backend.schemas.base import BaseSnakeRequest, UserEmail, NonEmptyString


class UserAuth(BaseSnakeRequest):
    email: UserEmail = Field(..., description="Электронная почта")
    password: NonEmptyString = Field(..., min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")
