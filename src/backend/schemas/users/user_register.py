from pydantic import Field

from src.backend.schemas.base import (BaseSnakeRequest, Password, UserEmail,
                                      Username)


class UserRegister(BaseSnakeRequest):
    email: UserEmail = Field(..., description="Электронная почта")
    password: Password = Field(..., description="Пароль, от 8 до 50 знаков")
    password_check: Password = Field(..., description="Пароль, от 8 до 50 знаков")
    username: Username = Field(..., description="Имя, от 3 до 50 символов")
