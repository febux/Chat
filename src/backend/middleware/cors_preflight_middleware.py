"""
CORS preflight middleware for FastAPI.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class FastCORSPreflight(BaseHTTPMiddleware):
    """
    Preflight middleware for FastAPI using CORS.
    """

    def __init__(self, app, allow_origin="*", allow_headers="*", allow_methods="*"):
        super().__init__(app)
        self.headers = {
            "access-control-allow-origin": allow_origin,
            "access-control-allow-headers": allow_headers,
            "access-control-allow-methods": allow_methods,
            "access-control-max-age": "600",
        }

    async def dispatch(self, request: Request, call_next):
        """
        Handles preflight requests for CORS.
        Only responds to preflight requests with appropriate headers.
        OPTIONS requests are allowed by default.

        :param request: The incoming FastAPI Request object.
        :param call_next: A coroutine function that represents the next middleware or endpoint in the request processing chain.
        :return: The response object or the next middleware in the chain.
        """
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=self.headers)
        response = await call_next(request)
        return response
