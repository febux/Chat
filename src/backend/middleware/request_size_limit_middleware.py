"""
Request size limit middleware
"""

from fastapi.requests import Request
from fastapi.responses import JSONResponse
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    This middleware checks if the incoming request has a payload size exceeding a certain limit.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Checks the request payload size and responds with a 413 status code if it exceeds the limit.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: The outgoing response object.
        """
        REQUEST_SIZE_LIMIT = request.app.state.app_config.REQUEST_SIZE_LIMIT
        if REQUEST_SIZE_LIMIT and int(request.headers.get("content-length", 0)) > REQUEST_SIZE_LIMIT:
            return JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={"detail": "Payload too large"},
            )
        return await call_next(request)
