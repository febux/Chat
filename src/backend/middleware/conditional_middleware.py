"""
Conditional middleware for specific endpoints.
"""

from fastapi.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware


class ConditionalMiddleware(BaseHTTPMiddleware):
    """
    This middleware checks if the incoming request is for a specific endpoint (e.g., "/admin").

    Note: This middleware should be used as a last middleware in the middleware stack.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Checks if the incoming request is for a specific endpoint and skips the middleware chain for other endpoints.

        :param request: The incoming FastAPI Request object.
        :param call_next: A coroutine function that represents the next middleware or endpoint in the request processing chain
        :return: The response object or the next middleware in the chain
        """
        if request.url.path.startswith("/admin"):
            # Only apply for /admin endpoints
            # TODO: Implement your conditional logic here
            pass
        return await call_next(request)
