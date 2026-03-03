"""
Logger provider function for FastAPI.

This function is designed to provide the application's logger instance to FastAPI endpoints.
It retrieves the logger from the Starlette request object and returns them as an instance of the `Logger` class.
"""

from typing import Annotated

from fastapi import Depends
from starlette.requests import Request

from src.core.logger.logger_factory import AppLogger


async def get_logger(request: Request) -> AppLogger:
    """
    This function retrieves a Logger instance associated with the incoming FastAPI request.

    :param request: The incoming FastAPI request. It is used to access the application state,
                    where the Logger instance is stored.

    :return: A Logger instance associated with the request.
    """
    return request.app.state.logger


LoggerService = Annotated[AppLogger, Depends(get_logger)]
