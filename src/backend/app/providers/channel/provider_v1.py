"""
Channel service provider function for FastAPI.
"""

from starlette.requests import Request

from src.backend.app.providers.orm_manager import OrmRepositoryManagerProvider
from src.backend.app.services.channel.service_v1 import ChannelService


async def get_channel_api_service(
    request: Request,
    orm_manager: OrmRepositoryManagerProvider,
) -> ChannelService:
    """
    Creates and returns a ChannelService instance.

    :param request: The FastAPI Request object.
    :param orm_manager: An instance of OrmRepositoryManager.
    :return: A ChannelService instance.
    """
    return ChannelService(orm_manager)
