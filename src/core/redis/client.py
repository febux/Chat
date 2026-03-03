"""
Redis client using asyncio for asynchronous Redis operations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable

import redis.asyncio as redis
from pydantic import RedisDsn

from src.core.logger.logger_factory import logger_bind

logger = logger_bind("RedisClient")


class RedisClient:
    """
    A client for interacting with a Redis server using asyncio.
    """

    def __init__(self, redis_url: RedisDsn, pool: bool = False) -> None:
        """
        Initialize the Redis client.

        :param redis_url: Redis URL.
        :param pool: Whether to use a connection pool for Redis connections.
        """
        self.redis_url = redis_url
        self.pool = pool
        self._client = self._create_redis_client()

    def _create_redis_client(self) -> redis.Redis:
        """
        Create and return a Redis client instance.

        :return: The Redis client instance.
        """
        logger.debug(f"Initializing Redis client: {self.redis_url} with pool={self.pool}")
        if self.pool:
            pool_connection = redis.ConnectionPool.from_url(str(self.redis_url))
            client = redis.Redis(
                connection_pool=pool_connection,
                retry_on_timeout=True,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=30,
                max_connections=10,
            )
        else:
            client = redis.Redis.from_url(str(self.redis_url), decode_responses=True)

        logger.debug("Redis client initialized")
        return client

    @property
    def client(self) -> redis.Redis:
        """
        Get the Redis client instance.

        :return: The Redis client instance.
        """
        return self._client

    async def close_connection(self):
        """
        Close the Redis connection asynchronously.

        This method should be called when the client is no longer needed to
        properly release the connection.
        """
        await self.client.close()

    async def _reconnect(self) -> None:
        """
        Attempt to reconnect to the Redis server if the client is disconnected.

        This method should be called when the client encounters a connection error
        or a timeout error.
        """
        logger.info("Reconnecting Redis client...")
        try:
            await self._client.close()
        except Exception as e:
            logger.warning(f"Error closing Redis client during reconnect: {e}")
        self._client = self._create_redis_client()

    async def _execute_with_reconnect(
        self,
        func: Callable,
        *args,
        retries: int = 3,
        delay: float = 1.0,
        **kwargs,
    ) -> Any:
        """
        Execute the specified function with automatic reconnect.

        :param func: The function to execute.
        :param args: The positional arguments to pass to the function.
        :param kwargs: The keyword arguments to pass to the function.
        :param retries: The maximum number of retries to attempt.
        :param delay: The delay in seconds between retries.
        :return: The result of the function.
        """
        last_exc = None
        for attempt in range(retries):
            try:
                return await func(*args, **kwargs)
            except (redis.ConnectionError, redis.TimeoutError) as e:
                last_exc = e
                logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}. Reconnecting...")
                await self._reconnect()
                await asyncio.sleep(delay)
        if last_exc is not None:
            logger.error(f"Failed to execute function after all retries: {last_exc}")
            raise last_exc
        else:
            raise RuntimeError("Failed to execute function after all retries")

    async def get(self, key) -> bytes | None:
        """
        Retrieve a value from Redis using the specified key.

        :param key: The key to retrieve the value for.
        :return: The value associated with the key, or None if the key doesn't exist.
        """
        return await self._execute_with_reconnect(self._client.get, key)

    async def increment(self, key) -> int | None:
        """
        Retrieve a value from Redis using the specified key.

        :param key: The key to retrieve the value for.
        :return: The value associated with the key, or None if the key doesn't exist.
        """
        return await self._execute_with_reconnect(self._client.incr, key)

    async def expire_at(self, key: bytes | str | memoryview, when: timedelta) -> bytes | None:
        """
        Retrieve a value from Redis using the specified key.

        :param key: The key to retrieve the value for.
        :param when: The timestamp (in seconds since the Unix epoch) when the key should expire.
        :return: The value associated with the key, or None if the key doesn't exist.
        """
        expire_time = int((datetime.now() + when).timestamp())
        return await self._execute_with_reconnect(self._client.expireat, key, expire_time)

    async def set(self, key, value, **kwargs):
        """
        Set a key-value pair in Redis.

        :param key: The key to set.
        :param value: The value to set.
        :param kwargs: Additional arguments to pass to the Redis set command.
        """
        return await self._execute_with_reconnect(self._client.set, key, value, **kwargs)


def redis_client_factory(redis_url: RedisDsn, pool: bool = False):
    """
    Factory function to create and return a Redis client instance.

    This function creates either a RedisClient or a RedisClientPool instance
    based on the 'pool' parameter. It provides a convenient way to obtain
    the appropriate Redis client for different use cases.

    :param redis_url: Redis URL.
    :param pool: A boolean flag indicating whether to create a RedisClientPool
                 (True) or a single RedisClient (False). Defaults to False.
    :return: An instance of either RedisClient.
    """
    return RedisClient(redis_url, pool=pool)
