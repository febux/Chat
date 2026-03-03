"""
Exception middleware for handling exceptions
"""

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.logger import AppLogger


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    ExceptionHandlerMiddleware is a FastAPI middleware that handles exceptions raised during request processing.

    It catches httpx.ConnectError exceptions and raises a ConnectionFailedException with the exception details.
    For any other exception, it raises a BaseAppException with the exception details.
    """

    def __init__(self, app: ASGIApp, logger: AppLogger) -> None:
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Handles incoming requests and dispatches them to the next middleware or endpoint.
        Catches exceptions raised during processing and handles them accordingly.

        :param request: The incoming FastAPI Request object.
        :param call_next: A coroutine function that represents the next middleware or endpoint in the request processing chain.
        :return: A Starlette Response object representing the response to the client.
        """
        try:
            return await call_next(request)
        except httpx.ConnectError as exc:
            self.logger.exception(f"Connection Failed: {exc}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Connection Failed",
                    "details": str(exc),
                },
            )
        except Exception as exc:
            """
            If the base exception was caught then the code should be checked double
            This exception mustn't be caught and also this exception mustn't be handled by general exception handler!
            """
            self.logger.exception(f"Unhandled exception: {exc}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "details": str(exc),
                },
            )
