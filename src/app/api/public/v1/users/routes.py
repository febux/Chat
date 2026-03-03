"""
Users API routes for the application.
"""

from typing import Annotated, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.requests import Request

from src.app.utils.current_user import get_current_user
from src.app.providers.user.provider_v1 import get_user_api_service
from src.app.services.user.meta import UserServiceMeta
from src.schemas.users.user_get import User

router = APIRouter()


@router.get(
    "",
    description="Get all users except for the current user",
    response_model=list[User],
    tags=["user"],  # Included in the OpenAPI documentation.
)
async def get_users(
    request: Request,
    service: Annotated[UserServiceMeta, Depends(get_user_api_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Sequence[User]:
    """
    Get all users from the database except for the current user.

    :param request: The FastAPI Request object.
    :return: A list of all users.
    """
    return await service.get_all_except_of_current_user(user_id=current_user.id)


@router.get(
    "/{user_id}",
    description="Get one user by ID",
    response_model=User,
    tags=["user"],  # Included in the OpenAPI documentation.
)
async def get_user_by_id(
    request: Request,
    user_id: UUID,
    service: Annotated[UserServiceMeta, Depends(get_user_api_service)],
) -> User:
    """
    Get one user by their ID from the database.

    :param request: The FastAPI Request object.
    :param user_id: The ID of the user to retrieve.
    :return: The user with the given ID.
    """
    return await service.get_by_id(user_id)
