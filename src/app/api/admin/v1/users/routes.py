"""
Common API routes for the application.
"""

from typing import Annotated, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from starlette.requests import Request

from src.app.utils.common_query_params import CommonQueryParams
from src.app.providers.user.provider_v1 import get_user_api_service
from src.app.services.user.meta import UserServiceMeta
from src.schemas.users.user_get import User

router = APIRouter()


@router.get(
    "",
    description="Get all users",
    response_model=list[User],
    tags=["user"],  # Included in the OpenAPI documentation.
)
async def get_users(
    request: Request,
    query: Annotated[CommonQueryParams, Query()],
    service: Annotated[UserServiceMeta, Depends(get_user_api_service)],
) -> Sequence[User]:
    """
    Get all users from the database.

    :param request: The FastAPI Request object.
    :return: A list of all users.
    """
    return await service.get_all(
        q=query.q,
        skip=query.skip,
        limit=query.limit,
    )


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
