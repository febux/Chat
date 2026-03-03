"""
Message service provider function for FastAPI.
"""

from starlette.requests import Request

from src.app.providers.orm_manager import OrmRepositoryManagerProvider
from src.app.services.message.service_v1 import MessageService


async def get_message_api_service(
    request: Request,
    orm_manager: OrmRepositoryManagerProvider,
) -> MessageService:
    """
    Creates and returns a MessageService instance.

    :param request: The FastAPI Request object.
    :param orm_manager: An instance of OrmRepositoryManager.
    :return: A MessageService instance.
    """
    return MessageService(orm_manager)
