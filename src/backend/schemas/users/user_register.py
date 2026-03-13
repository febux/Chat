from pydantic import Field

from src.backend.schemas.base import BaseSnakeRequest, UserEmail, NonEmptyString


class UserRegister(BaseSnakeRequest):
    email: UserEmail = Field(..., description="Электронная почта")
    password: NonEmptyString = Field(..., min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")
    password_check: NonEmptyString = Field(..., min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")
    username: NonEmptyString = Field(..., min_length=3, max_length=50, description="Имя, от 3 до 50 символов")
