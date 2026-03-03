"""
User service provider function for FastAPI.
"""

from starlette.requests import Request

from src.app.providers.orm_manager import OrmRepositoryManagerProvider
from src.app.services.user.service_v1 import UserService


async def get_user_api_service(
    request: Request,
    orm_manager: OrmRepositoryManagerProvider,
) -> UserService:
    """
    Creates and returns a UserService instance.

    :param request: The FastAPI Request object.
    :param orm_manager: An instance of OrmRepositoryManager.
    :return: A UserService instance.
    """
    return UserService(orm_manager)
