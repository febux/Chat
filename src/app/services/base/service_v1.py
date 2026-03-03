"""
Base API service implementation V1.
"""

import redis.asyncio as redis
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.config.main import Settings
from src.core.logger.app_logger import AppLogger


class BaseApiService:
    """
    A service class for handling base operations.
    """

    def __init__(
        self,
        app_config: Settings,
        redis_client: redis.Redis,
        session: AsyncSession,
        logger: AppLogger,
    ):
        self.app_config = app_config
        self.redis_client = redis_client
        self.session = session
        self.logger = logger

    async def healthcheck(self, request: Request) -> JSONResponse:
        """
        Health check endpoint for the API service.

        :param request: The FastAPI Request object.
        :return: A response indicating the health of the API service.
        """
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "healthy"},
        )

    async def system_metrics(self, request: Request) -> JSONResponse:
        """
        Detailed metrics endpoint for monitoring and alerting.

        :param request: The FastAPI Request object.
        :return: Metrics for the API service and connected services.
        """
        pass
