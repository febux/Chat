"""
This middleware adds security headers to the response.
It sets the X-Content-Type-Options header to "nosniff" and the X-Frame-Options header to "DENY".
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeaderPostureMiddleware(BaseHTTPMiddleware):
    """
    This middleware adds security headers to the response.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Adds security headers to the response.

        :param request: The incoming FastAPI Request object.
        :param call_next: A coroutine function that represents the next middleware or endpoint in the request processing chain.
        :return: The outgoing response object with security headers added.
        """
        response = await call_next(request)
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Feature-Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"

        # HTTPS enforcement
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Content Security Policy
        # response.headers["Content-Security-Policy"] = (
        #     "default-src 'self'; "
        #     "script-src 'self'; "
        #     "style-src 'self' 'unsafe-inline'; "
        #     "img-src 'self' data: https:;"
        # )
        return response
