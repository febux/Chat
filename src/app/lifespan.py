"""
Lifespan of the FastAPI application.
"""

import asyncio
from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI

from src.core.nats.client import nats_client_factory
from src.config.main import settings
from src.core.adapters_loader import auto_register_adapters
from src.core.logger.logger_factory import logger_bind
from src.core.redis.client import redis_client_factory
from src.database.sqlalchemy.utils import sessionmanager
from src.utils.cascade_lifespans import cascade_lifespan

_logger = logger_bind(settings.app.APP_NAME)


@asynccontextmanager
async def app_lifespan(app_: FastAPI):
    """
    Manages the lifecycle of the FastAPI application.

    This asynchronous context manager handles the initialization and shutdown
    processes of the application. It sets up the Redis client, configures
    application state, and performs cleanup operations when the app is shutting down.

    :param app_: The FastAPI application instance to which the lifespan is being applied.
    """
    async with cascade_lifespan(app_):
        # code to execute when app is loading
        _logger.info("Starting app")
        loop = asyncio.get_running_loop()
        _logger.info(f"Event loop: {str(type(loop))}")

        # Redis
        try:
            redis_client = redis_client_factory(redis_url=settings.redis.get_redis_url(), pool=True)
            await redis_client.client.ping()
        except redis.exceptions.ConnectionError as e:
            _logger.error(f"Failed to initialize Redis client connection: {e}")
            app_.state.redis_client = None
        else:
            _logger.info("Redis client connection initialized", url=settings.redis.get_redis_url())
            app_.state.redis_client = redis_client.client

        # NATS socket manager
        try:
            if getattr(app_.state, "socket_manager", None) is not None:
                await app_.state.socket_manager.connect_nats()
        except Exception as e:
            _logger.error(f"Failed to initialize Socket manager with NATS client connection: {e}")
        else:
            _logger.info("Socket manager with NATS client connection initialized", url=settings.nats.get_nats_url())

        # Auto-register adapters
        auto_register_adapters(
            app_,
            adapter_path="src/app/adapters",
            logger=_logger,
        )

        yield
        # code to execute when app is shutting down
        _logger.info("Stopping app")

        if getattr(app_.state, "socket_manager", None) is not None:
            await app_.state.socket_manager.disconnect_nats()
            _logger.info("Socket manager with NATS client connection closed")

        if sessionmanager.engine is not None:
            # Close the DB connection
            await sessionmanager.close()
            _logger.info("Database manager connection closed")

        if app_.state.redis_client:
            await app_.state.redis_client.close()
            _logger.info("Redis client connection closed")

        # Cancel background tasks
        tasks = [task for task in asyncio.all_tasks() if not task.done()]
        if tasks:
            _logger.info(f"Cancelling {len(tasks)} pending tasks...")
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        _logger.info("Application stopped")
