"""
User service provider function for FastAPI.
"""

from starlette.requests import Request

from src.backend.app.providers.redis import RedisClient
from src.backend.app.providers.orm_manager import OrmRepositoryManagerProvider
from src.backend.app.services.user.service_v1 import UserService


async def get_user_api_service(
    request: Request,
    orm_manager: OrmRepositoryManagerProvider,
    redis_client: RedisClient,
) -> UserService:
    """
    Creates and returns a UserService instance.

    :param request: The FastAPI Request object.
    :param orm_manager: An instance of OrmRepositoryManager.
    :param redis_client: A Redis client instance.
    :return: A UserService instance.
    """
    return UserService(orm_manager, redis_client)
