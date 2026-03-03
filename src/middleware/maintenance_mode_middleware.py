"""
Maintenance mode status check middleware
"""

from fastapi.requests import Request
from fastapi.responses import JSONResponse
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.main import settings


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """
    This middleware checks if the application is in maintenance mode.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Checks if the application is in maintenance mode and returns a JSON response with a 503 status code if it is.

        :param request: The incoming FastAPI Request object.
        :param call_next: A coroutine function that represents the next middleware or endpoint in the request processing chain.
        :return: A Starlette Response object representing the response to the client.
        """
        if settings.app.MAINTENANCE_MODE:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Under maintenance"},
            )
        return await call_next(request)
