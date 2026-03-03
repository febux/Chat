"""
Message service provider function for FastAPI.
"""

from starlette.requests import Request

from src.app.providers.config import AppConfig
from src.app.providers.logger import LoggerService
from src.app.providers.orm_manager import OrmRepositoryManagerProvider
from src.app.services.message.service_v1 import MessageService


async def get_message_api_service(
    request: Request,
    app_config: AppConfig,
    orm_manager: OrmRepositoryManagerProvider,
    logger: LoggerService,
) -> MessageService:
    """
    Creates and returns a MessageService instance.

    :param request: The FastAPI Request object.
    :param app_config: An instance of AppConfig.
    :param orm_manager: An instance of OrmRepositoryManager.
    :param logger: An instance of LoggerService.
    :return: A MessageService instance.
    """
    return MessageService(app_config, orm_manager, logger)
