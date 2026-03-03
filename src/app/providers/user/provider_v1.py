"""
User service provider function for FastAPI.
"""

from starlette.requests import Request

from src.app.providers.config import AppConfig
from src.app.providers.logger import LoggerService
from src.app.providers.orm_manager import OrmRepositoryManagerProvider
from src.app.services.user.service_v1 import UserService


async def get_user_api_service(
    request: Request,
    app_config: AppConfig,
    orm_manager: OrmRepositoryManagerProvider,
    logger: LoggerService,
) -> UserService:
    """
    Creates and returns a UserService instance.

    :param request: The FastAPI Request object.
    :param app_config: An instance of AppConfig.
    :param orm_manager: An instance of OrmRepositoryManager.
    :param logger: An instance of LoggerService.
    :return: A UserService instance.
    """
    return UserService(app_config, orm_manager, logger)
