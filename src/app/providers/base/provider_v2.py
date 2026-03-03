"""
Proxy service provider function for FastAPI.

This module provides a function to retrieve a ProxyService instance, which is responsible for
communicating with the proxy service.
"""

from starlette.requests import Request

from src.app.providers.config import AppConfig
from src.app.providers.db import DbSession
from src.app.providers.logger import LoggerService
from src.app.providers.redis import RedisClient
from src.app.services.base.meta import BaseApiServiceMeta
from src.app.services.base.service_v2 import BaseApiService


async def get_service_api_service(
    request: Request,
    app_config: AppConfig,
    redis_client: RedisClient,
    session: DbSession,
    logger: LoggerService,
) -> BaseApiServiceMeta:
    """
    Creates and returns a ApiService instance.

    :param request: The FastAPI Request object.
    :param app_config: An instance of AppConfig.
    :param redis_client: An instance of RedisClient.
    :param session: An instance of the database session.
    :param logger: An instance of LoggerService.
    :return: A ApiServiceMeta instance.
    """
    return BaseApiService(app_config, redis_client, session, logger)
