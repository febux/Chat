from pydantic import Field

from src.backend.schemas.base import BaseSnakeRequest, Password, UserEmail


class UserAuth(BaseSnakeRequest):
    email: UserEmail = Field(..., description="Электронная почта")
    password: Password = Field(..., description="Пароль, от 8 до 50 знаков")
