"""
Centrifugo service provider function for FastAPI.
"""

from starlette.requests import Request

from src.backend.app.providers.orm_manager import OrmRepositoryManagerProvider
from src.backend.app.services.centrifugo.service_v1 import CentrifugoService


async def get_centrifugo_api_service(
    request: Request,
    orm_manager: OrmRepositoryManagerProvider,
) -> CentrifugoService:
    """
    Creates and returns a CentrifugoService instance.

    :param request: The FastAPI Request object.
    :param orm_manager: An instance of OrmRepositoryManager.
    :return: A CentrifugoService instance.
    """
    return CentrifugoService(orm_manager)
