from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from jose import JWTError, jwt

from src.backend.app.providers.user.provider_v1 import get_user_api_service
from src.backend.app.services.user.meta import UserServiceMeta
from src.backend.common.exceptions.api.token_exceptions import (
    InvalidJwtError, TokenExpiredError, TokenNotFoundError)
from src.backend.common.exceptions.api.user_exceptions import (
    UserIdNotFoundError, UserNotFoundError)
from src.backend.config.main import settings
from src.backend.schemas.users.user_get import User
from src.backend.utils.cookie import get_cookie


def get_token(request: Request):
    token = get_cookie(request, 'users_access_token')
    if not token:
        raise TokenNotFoundError
    return token


async def get_current_user(
    service: Annotated[UserServiceMeta, Depends(get_user_api_service)],
    token: str = Depends(get_token)
) -> User:
    try:
        payload = jwt.decode(token, settings.app.JWT_SECRET_KEY, algorithms=settings.app.JWT_ALGORITHM)
    except JWTError:
        raise InvalidJwtError

    expire = payload.get('exp')
    if not expire:
        raise InvalidJwtError
    try:
        expire_time = datetime.fromtimestamp(int(expire), tz=timezone.utc)
    except (TypeError, ValueError):
        raise InvalidJwtError
    if expire_time < datetime.now(timezone.utc):
        raise TokenExpiredError

    user_id: str = payload.get('sub')
    if not user_id:
        raise UserIdNotFoundError

    user = await service.get_by_id(UUID(user_id))
    if not user:
        raise UserNotFoundError
    return user
