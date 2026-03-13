"""
Base API router for authorization and others.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import RedirectResponse

from src.backend.app.utils.current_user import get_current_user
from src.backend.schemas.users.user_get import User
from src.backend.app.utils.auth import create_access_token
from src.backend.common.exceptions.api.user_exceptions import UserAlreadyExistsError
from src.backend.common.exceptions.api.password_exceptionx import PasswordMismatchError, IncorrectEmailOrPasswordError
from src.backend.app.providers.user.provider_v1 import get_user_api_service
from src.backend.app.services.user.meta import UserServiceMeta
from src.backend.schemas.users.user_auth import UserAuth
from src.backend.schemas.users.user_register import UserRegister
from src.backend.utils.password import hash_password

router = APIRouter()


@router.post(
    "/register",
    response_model=dict,
    status_code=201,
    tags=["authorization"],
    description="Register a new user",
)
async def register_user(
    user_data: UserRegister,
    service: Annotated[UserServiceMeta, Depends(get_user_api_service)],
) -> dict:
    user = await service.get_by_email(email=user_data.email)
    if user:
        raise UserAlreadyExistsError

    if user_data.password != user_data.password_check:
        raise PasswordMismatchError
    hashed_password = await hash_password(user_data.password)
    user = await service.create(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password
    )

    return {'message': 'Вы успешно зарегистрированы!', 'user_id': user.id}


@router.post(
    "/logout",
    tags=["authorization"],
)
async def logout(
    request: Request,
    response: RedirectResponse,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Logout the user and clear the session.

    :param request: Incoming FastAPI request.
    :param response: Redirect response object.
    :return: Redirect to the login page.
    """
    response.delete_cookie(key="users_access_token")
    response.delete_cookie(key="users_refresh_token")
    return {'message': 'Вы вышли из системы!'}


@router.post(
    "/login",
    tags=["authorization"],
)
async def login(
    user_data: UserAuth,
    request: Request,
    response: RedirectResponse,
    service: Annotated[UserServiceMeta, Depends(get_user_api_service)],
):
    """
    Login the user and set the session.

    :param request: Incoming FastAPI request.
    :param response: Redirect response object.
    :param service: User service provider.
    :return: Redirect to the home page.
    """
    check = await service.authenticate_user(email=user_data.email, password=user_data.password)
    if check is None:
        raise IncorrectEmailOrPasswordError
    access_token = create_access_token({"sub": str(check.id)})
    response.set_cookie(key="users_access_token", value=access_token, httponly=True)
    return {'access_token': access_token, 'refresh_token': None, 'message': 'Авторизация успешна!'}



@router.get(
    "/me",
    response_model=dict,
    summary="Получить данные текущего пользователя",
    status_code=200,
)
async def get_current_user_info(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Returns the data of the authorized user.
    Secure endpoint - requires a valid JWT token in the 'users_access_token' cookie.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.username,
        "is_active": getattr(current_user, 'is_active', True),
        "created_at": current_user.created_at.isoformat() if hasattr(current_user, 'created_at') else None
    }
