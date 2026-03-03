"""
Stream iteratively logging chunks sent to the response body.

Ensure that the `MAX_BODY_SIZE` variable is set to a reasonable value.
"""

from fastapi.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.logger import AppLogger


class StreamMiddleware(BaseHTTPMiddleware):
    """
    StreamMiddleware is a middleware for FastAPI that logs chunks sent to the response body.
    """

    def __init__(self, app: ASGIApp, logger: AppLogger) -> None:
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        """
        Dispatches the incoming request and logs the chunks sent to the response body.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: The outgoing response object.
        """
        response = await call_next(request)
        if hasattr(response, "body_iterator"):
            # Example: log chunks as they are sent
            async for chunk in response.body_iterator:
                self.logger.debug(f"Chunk sent: {chunk}")
        return response
