"""
Redis client provider function for FastAPI.

This function retrieves a Redis client instance associated with the incoming FastAPI request.
The Redis client instance is expected to be initialized and stored in the FastAPI request's app state.
"""

from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends
from starlette.requests import Request


async def get_redis_client(request: Request):
    """
    Retrieve the Redis client instance associated with the incoming FastAPI request.

    :param request: The incoming FastAPI request.
    :return: The Redis client instance associated with the incoming FastAPI request.
    """
    return request.app.state.redis_client


RedisClient = Annotated[redis.Redis, Depends(get_redis_client)]
