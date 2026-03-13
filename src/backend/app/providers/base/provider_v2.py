"""
Proxy service provider function for FastAPI.

This module provides a function to retrieve a ProxyService instance, which is responsible for
communicating with the proxy service.
"""

from starlette.requests import Request

from src.backend.app.providers.db import DbSession
from src.backend.app.providers.redis import RedisClient
from src.backend.app.services.base.meta import BaseApiServiceMeta
from src.backend.app.services.base.service_v2 import BaseApiService


async def get_service_api_service(
    request: Request,
    redis_client: RedisClient,
    session: DbSession,
) -> BaseApiServiceMeta:
    """
    Creates and returns a ApiService instance.

    :param request: The FastAPI Request object.
    :param redis_client: An instance of RedisClient.
    :param session: An instance of the database session.
    :return: A ApiServiceMeta instance.
    """
    return BaseApiService(redis_client, session)
