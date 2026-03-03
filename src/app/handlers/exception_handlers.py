"""
Exception handling in FastAPI can be done using the @app.exception_handler decorator.
You can also add exception handlers for specific exception types
using the @app.exception_handler(ExceptionType) decorator.
Here's an example of how you can add exception handlers to a FastAPI application.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from starlette import status
from starlette.responses import RedirectResponse

from src.common.exceptions.api.user_exceptions import UserNotFoundError
from src.common.exceptions.api.token_exceptions import TokenExpiredError, TokenNotFoundError
from src.common.exceptions.api import ServerAPIException
from src.common.exceptions.api.client_exception import ClientAPIException
from src.common.exceptions.common import ConnectionFailedException


def add_exceptions_handlers(app: FastAPI):
    """
    Adds exception handlers to a FastAPI application.

    :param app: The FastAPI application instance.
    :return: None
    """

    @app.exception_handler(ClientAPIException)
    async def http_client_error_handler(_: Request, exc: ClientAPIException) -> JSONResponse:
        """
        Handles ClientAPIException exceptions.

        :param _: The FastAPI Request object.
        :param exc: The ClientAPIException instance.
        :return: A JSONResponse with the exception details.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(ServerAPIException)
    async def http_server_error_handler(_: Request, exc: ServerAPIException) -> JSONResponse:
        """
        Handles ServerAPIException exceptions.

        :param _: The FastAPI Request object.
        :param exc: The ServerAPIException instance.
        :return: A JSONResponse with the exception details.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(ConnectionFailedException)
    async def connection_failed_handler(_: Request, exc: ConnectionFailedException) -> JSONResponse:
        """
        Handles ConnectionFailedException exceptions.

        :param _: The FastAPI Request object.
        :param exc: The ConnectionFailedException instance.
        :return: A JSONResponse with the exception details.
        """
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": exc.error,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Compact, user-friendly error structure

        :param request: The FastAPI Request object.
        :param exc: The RequestValidationError instance.
        :return: A JSONResponse with validation errors.
        """
        errors = [{"field": err["loc"][-1], "error": err["msg"]} for err in exc.errors()]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"errors": errors, "message": "Invalid request", "path": str(request.url)},
        )

    @app.exception_handler(TokenExpiredError)
    async def token_expired_exception_handler(request: Request, exc: TokenExpiredError):
        # Возвращаем редирект на страницу /auth
        return RedirectResponse(url="/auth")

    # Обработчик для TokenNoFound
    @app.exception_handler(TokenNotFoundError)
    async def token_not_found_exception_handler(request: Request, exc: TokenNotFoundError):
        # Возвращаем редирект на страницу /auth
        return RedirectResponse(url="/auth")

    @app.exception_handler(UserNotFoundError)
    async def user_id_not_found_exception_handler(request: Request, exc: UserNotFoundError):
        """
        Handles UserIdNotFoundError exceptions.

        :param request: The FastAPI Request object.
        :param exc: The UserIdNotFoundError instance.
        :return: redirect to /auth
        """
        return RedirectResponse(url="/auth")

