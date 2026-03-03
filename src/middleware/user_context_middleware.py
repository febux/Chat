"""
Injects user context into the request state middleware by checking the Authorization header for a valid JWT token.
"""

from fastapi import HTTPException
from jose import JWTError, jwt  # type: ignore[missing-module]
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.config.main import settings


class UserInjectContextMiddleware(BaseHTTPMiddleware):
    """
    This middleware injects user context into the request state by checking the Authorization header for a valid JWT token.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Injects user context into the request state by checking the Authorization header for a valid JWT token.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: The outgoing response object.
        """
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, settings.app.JWT_SECRET_KEY, algorithms=[settings.app.JWT_ALGORITHM])
                request.state.user = payload
            except JWTError:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        else:
            request.state.user = None

        return await call_next(request)
