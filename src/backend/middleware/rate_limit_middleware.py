"""
Rate limiter middleware for limiting the number of requests a client can make to a specific endpoint within a certain time duration.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

from src.backend.common.exceptions.api.server_exception import ServerAPIException
from src.backend.config.main import settings
from src.backend.core.redis.client import RedisClient

default_limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis.get_redis_url())


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for limiting the number of requests a client can make to a specific endpoint within a certain time duration.
    """

    def __init__(
        self,
        app: FastAPI,
        *,
        limit_duration: int = 1,
        limit_requests: int = 3,
        redis_client: RedisClient | None = None,
    ):
        """
        Initializes the rate limiting middleware.

        :param app: The FastAPI application.
        :param limit_duration: The duration in minutes for which the client's requests will be limited. Defaults to 1 minute.
        :param limit_requests: The maximum number of requests allowed within the specified time duration. Defaults to 3.
        :param redis_client: The Redis client or client pool to use for rate limiting.
        """
        super().__init__(app)
        self.RATE_LIMIT_DURATION = timedelta(minutes=limit_duration)
        self.RATE_LIMIT_REQUESTS = limit_requests
        self.request_counts: dict[str, tuple[int | Any, datetime]] = {}
        self._redis_client = redis_client

    async def _in_memory_dispatch(self, request, call_next):
        """
        Dispatches the incoming request and handles rate limiting using in-memory storage.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: The outgoing response object.
        """
        # Get the client's IP address
        client_ip = request.client.host
        now = datetime.now(UTC)
        # Check if IP is already present in request_counts
        request_count, last_request = self.request_counts.get(client_ip, (0, datetime.min))

        # Calculate the time elapsed since the last request
        elapsed_time = now - last_request

        if elapsed_time > self.RATE_LIMIT_DURATION:
            # If the elapsed time is greater than the rate limit duration, reset the count
            request_count = 1
        else:
            if request_count >= self.RATE_LIMIT_REQUESTS:
                # If the request count exceeds the rate limit, return a JSON response with an error message
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit error",
                        "details": "Rate limit exceeded. Please try again later.",
                    },
                    headers={
                        "Retry-After": f"{60 - now.second}",
                        "X-Rate-Limit": f"{self.RATE_LIMIT_REQUESTS}",
                    },
                )
            request_count += 1

        # Update the request count and last request timestamp for the IP
        self.request_counts[client_ip] = (request_count, now)

        # Proceed with the request
        response = await call_next(request)
        return response

    async def _redis_dispatch(self, request, call_next):
        """
        Dispatches the incoming request and handles rate limiting using Redis storage.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: The outgoing response object.
        """
        if not self._redis_client:
            raise ServerAPIException(
                loc=[
                    "query",
                    "rate_limit_key",
                ],
                msg="Redis client is not available",
                error_type="server_error.redis_not_available",
            )

        username_hash = hashlib.sha256(bytes(request.client.host, "utf-8")).hexdigest()
        now = datetime.now(UTC)
        current_minute = now.strftime("%Y-%m-%dT%H:%M")
        # Increment our most recent redis key
        redis_key = f"rate_limit_{username_hash}_{current_minute}"
        current_count = await self._redis_client.increment(redis_key)

        # If we just created a new key (count is 1) set an expiration
        if current_count == 1:
            await self._redis_client.expire_at(key=redis_key, when=self.RATE_LIMIT_DURATION)

        # Check rate limit
        if current_count > self.RATE_LIMIT_REQUESTS:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit error",
                    "details": "Rate limit exceeded. Please try again later.",
                },
                headers={
                    "Retry-After": f"{60 - now.second}",
                    "X-Rate-Limit": f"{self.RATE_LIMIT_REQUESTS}",
                },
            )

        # Proceed with the request
        response = await call_next(request)
        return response

    async def dispatch(self, request, call_next):
        """
        Dispatches the incoming request and applies rate limiting.

        :param request: The incoming FastAPI Request object.
        :param call_next: A coroutine function that represents the next middleware or endpoint in the request processing chain.
        :return: A Starlette Response object representing the response to the client.
        """
        # Check if Redis client is provided
        if self._redis_client is not None:
            return await self._redis_dispatch(request, call_next)
        else:
            # If Redis client is not provided, use in-memory rate limiting
            return await self._in_memory_dispatch(request, call_next)
