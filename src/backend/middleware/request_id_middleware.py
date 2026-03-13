"""
Request ID Middleware which generates a unique request ID for each incoming request.
"""

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    This middleware adds a unique request ID to each incoming request.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Adds a unique request ID to the incoming request and propagates it to the response.

        :param request: The incoming FastAPI Request object.
        :param call_next: A coroutine function that represents the next middleware or endpoint in the request processing chain.
        :return: A Starlette Response object representing the response to the client.
        """
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id  # store it in request context

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id  # propagate to response
        return response
