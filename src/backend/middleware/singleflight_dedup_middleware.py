"""
SingleflightMiddleware is a middleware for FastAPI that implements the "Singleflight" pattern.

The middleware ensures that only one request with the same path and query parameters is processed at a time.

If a request with the same path and query parameters is received, the middleware immediately returns the result from the previous request.

This pattern is useful for optimizing resource usage and reducing the number of concurrent requests.
"""

import asyncio
from typing import Dict, Iterable, Optional, Union

import orjson
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.backend.core.logger import AppLogger

# Configuration constants
MAX_BODY_SIZE = 1024 * 1024  # 1MB limit for bodies


class SingleflightMiddleware(BaseHTTPMiddleware):
    """
    SingleflightMiddleware is a middleware for FastAPI that implements the "Singleflight" pattern.

    Attributes:
        app: The FastAPI application.
        logger: The logger instance.
    Vars:
        lock: The asyncio Lock object for synchronization.
        pending: A dictionary to store pending requests, where the keys are unique keys and the values are asyncio Futures.
    """

    def __init__(self, app: ASGIApp, logger: AppLogger) -> None:
        super().__init__(app)
        self.logger = logger
        self.lock = asyncio.Lock()
        self.pending: dict[str, asyncio.Future] = {}

    def _key(self, request):
        """
        Generate a unique key for the request.

        :param request: The incoming FastAPI Request object.
        :return: The unique key for the
        """
        if request.method != "GET":
            return None
        return f"{request.url.path}?{request.url.query}"

    async def _get_response_body_safe(self, response: Response) -> Optional[Union[Dict, str]]:
        """
        Safe response body extraction with streaming support.

        :param response: The incoming FastAPI Response object.
        :return: The response body as a string or JSON object, or None if the body is too large.
        """
        if not hasattr(response, "body_iterator"):
            return None

        try:
            # Collect response chunks efficiently
            body_chunks = []
            total_size = 0

            async for chunk in response.body_iterator:
                if total_size + len(chunk) > MAX_BODY_SIZE:
                    body_chunks.append(f"<response truncated at {MAX_BODY_SIZE} bytes>".encode())
                    break
                body_chunks.append(chunk)
                total_size += len(chunk)

            # Reconstruct body iterator for client
            response.body_iterator = self._async_iter_chunks(body_chunks)

            # Parse collected body
            if body_chunks:
                full_body = b"".join(body_chunks)
                try:
                    text = full_body.decode("utf-8")
                    if text.strip().startswith(("{", "[")):
                        return orjson.loads(text)
                    return text
                except (UnicodeDecodeError, orjson.JSONDecodeError):
                    return f"<binary/invalid content: {len(full_body)} bytes>"

            return None

        except Exception as e:
            self.logger.exception(f"Error extracting response body: {str(e)}")
            return None

    async def _async_iter_chunks(self, chunks: Iterable):
        """
        Async iterator for response chunks.

        :param chunks: The response chunks.
        :return: The response chunks as an async iterator.
        """
        for chunk in chunks:
            yield chunk

    async def dispatch(self, request, call_next):
        """
        Dispatches the incoming request and handles the "Singleflight" pattern.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: The outgoing response object.
        """
        key = self._key(request)
        if not key:
            return await call_next(request)

        async with self.lock:
            fut = self.pending.get(key)
            if fut is None or fut.done():
                fut = self.pending[key] = asyncio.get_event_loop().create_future()

                async def run():
                    """
                    Run the next middleware or endpoint and store the result in the future.
                    """
                    resp = await call_next(request)
                    body = await resp.body()
                    fut.set_result((resp.status_code, dict(resp.headers), body))
                    async with self.lock:
                        if ft := self.pending.pop(key, None):
                            await ft

                asyncio.create_task(run())

        status, headers, body = await fut
        return Response(content=body, status_code=status, headers=headers)
