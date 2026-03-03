"""
Redis client provider function for FastAPI.

This function retrieves a Redis client instance associated with the incoming FastAPI request.
The Redis client instance is expected to be initialized and stored in the FastAPI request's app state.
"""

from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends

from src.config.main import settings
from src.core.redis.client import redis_client_factory


async def get_redis_client():
    """
    Retrieve the Redis client instance associated with the incoming FastAPI request.

    :return: The Redis client instance associated with the incoming FastAPI request.
    """
    return redis_client_factory(redis_url=settings.redis.get_redis_url(), pool=True)


RedisClient = Annotated[redis.Redis, Depends(get_redis_client)]
