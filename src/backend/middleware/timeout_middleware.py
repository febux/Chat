"""
Timeout middleware for setting a timeout for incoming requests.
"""

import asyncio

from fastapi.requests import Request
from fastapi.responses import JSONResponse
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Timeout middleware for setting a timeout for incoming requests.
    """

    def __init__(self, app, timeout: int):
        """
        Initialize the TimeoutMiddleware.

        :param app: The FastAPI application.
        :param timeout: The timeout duration in seconds.
        """
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        """
        Dispatches the incoming request and handles timeouts.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: The outgoing response object.
        """
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return JSONResponse(status_code=status.HTTP_504_GATEWAY_TIMEOUT, content="Request timed out")
