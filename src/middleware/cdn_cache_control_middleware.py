"""
CDN cache headers middleware for FastAPI.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class CDNCacheHeaders(BaseHTTPMiddleware):
    """
    Middleware for FastAPI that adds cache headers for CDNs.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Adds cache headers for CDNs.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: The outgoing response object with cache headers added.
        """
        response = await call_next(request)
        if request.method == "GET" and response.status_code == 200:
            # public for CDNs, brief micro-TTL, and fast revalidation
            response.headers.setdefault("Cache-Control", "public, s-maxage=15, stale-while-revalidate=60")
            # helpful for some CDNs:
            response.headers.setdefault("Surrogate-Control", "max-age=15, stale-while-revalidate=60")
        return response
