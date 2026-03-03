"""
Configuration provider function for FastAPI.

This function is designed to provide the application's configuration settings to FastAPI endpoints.
It retrieves the settings from the Starlette request object and returns them as an instance of the `Settings` class.
"""

from typing import Annotated

from fastapi import Depends
from starlette.requests import Request

from src.config.main import Settings, settings


async def get_settings(request: Request) -> Settings:
    """
    Retrieve the application's configuration settings from the Starlette request object.

    :param request: The Starlette request object, which contains the application state.
    :return: An instance of the `Settings` class containing the application's configuration settings.
    """
    return settings


AppConfig = Annotated[Settings, Depends(get_settings)]
