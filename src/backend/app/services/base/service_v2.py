"""
Base API service implementation V2.
"""

import asyncio
import os
from datetime import datetime

import psutil  # type: ignore[missing-module]
import redis.asyncio as redis
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.backend.config.main import settings
from src.backend.core.logger.logger_factory import logger_bind


class BaseApiService:
    """
    A service class for handling base operations.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        session: AsyncSession,
    ):
        self.app_config = settings
        self.redis_client = redis_client
        self.session = session
        self.logger = logger_bind("BaseApiService")

    async def healthcheck(self, request: Request) -> JSONResponse:
        """
        Health check endpoint for the API service.

        :param request: The FastAPI Request object.
        :return: A response indicating the health of the API service, Redis and DB.
        """

        try:
            await self.redis_client.ping()
            redis_status = {"status": "connected"}
        except Exception as e:
            redis_status = {"status": "disconnected", "error": str(e)}
            self.logger.error(f"Failed to check Redis connection: {e}")

        try:
            await self.session.execute(text("SELECT 1"))
            db_status = {"status": "connected"}
        except Exception as e:
            db_status = {"status": "disconnected", "error": str(e)}
            self.logger.error(f"Failed to check database connection: {e}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "timestamp": datetime.now().isoformat(),
                "status": "healthy",
                "services": {
                    "redis": redis_status,
                    "database": db_status,
                },
                "worker_pid": os.getpid(),
                "active_connections": len(asyncio.all_tasks()),
            },
        )

    async def system_metrics(self, request: Request) -> JSONResponse:
        """
        Detailed metrics endpoint for monitoring and alerting.

        :param request: The FastAPI Request object.
        :return: Metrics for the API service and connected services.
        """
        # Get system-wide metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        # Get this worker's specific metrics
        process = psutil.Process(os.getpid())
        worker_cpu = process.cpu_percent()
        worker_memory = process.memory_info()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "timestamp": datetime.now().isoformat(),
                "system_metrics": {
                    "cpu_usage_percent": cpu_percent,
                    "total_memory_gb": round(memory.total / (1024**3), 2),
                    "available_memory_gb": round(memory.available / (1024**3), 2),
                    "memory_usage_percent": memory.percent,
                },
                "worker_metrics": {
                    "worker_pid": os.getpid(),
                    "worker_cpu_percent": worker_cpu,
                    "worker_memory_mb": round(worker_memory.rss / (1024**2), 2),
                    "active_tasks": len(asyncio.all_tasks()),
                },
                "recommendations": {
                    "cpu_status": "OK" if cpu_percent < 80 else "HIGH - Consider scaling",
                    "memory_status": "OK" if memory.percent < 85 else "HIGH - Check for memory leaks",
                    "worker_status": "OK" if worker_cpu < 90 else "OVERLOADED - Increase workers",
                },
            },
        )
