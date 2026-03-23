"""
Users API routes for the application.
"""

from typing import Annotated, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.requests import Request

from src.backend.app.utils.current_user import get_current_user
from src.backend.app.providers.user.provider_v1 import get_user_api_service
from src.backend.app.services.user.meta import UserServiceMeta
from src.backend.schemas.users.user_get import User

router = APIRouter(tags=["user"])


@router.get(
    "",
    description="Get all users except for the current user",
    response_model=list[User],
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
)
async def get_user_by_id(
    request: Request,
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserServiceMeta, Depends(get_user_api_service)],
) -> User:
    """
    Get one user by their ID from the database.

    :param request: The FastAPI Request object.
    :param user_id: The ID of the user to retrieve.
    :param current_user: The current user making the request.
    :return: The user with the given ID.
    """
    return await service.get_by_id(user_id)


@router.post(
    "/ping",
    description="Ping the current user to indicate is still active",
    response_model=dict[str, bool],
)
async def user_ping(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserServiceMeta, Depends(get_user_api_service)],
):
    """
    Ping the current user to indicate is still active.

    :param current_user: The current user making the request.
    :param service: The User service instance.
    :return: A success message.
    """
    await service.set_user_ping(user_id=current_user.id)
    return {"ok": True}
