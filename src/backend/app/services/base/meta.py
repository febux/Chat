"""
This module defines the protocol for proxy services.
"""

from abc import abstractmethod
from typing import Protocol

from fastapi.requests import Request
from fastapi.responses import JSONResponse


class BaseApiServiceMeta(Protocol):
    """
    Protocol for API services.
    """

    @abstractmethod
    async def healthcheck(self, request: Request) -> JSONResponse:
        """
        Health check endpoint for the API service.
        """
        ...

    @abstractmethod
    async def system_metrics(self, request: Request) -> JSONResponse:
        """
        Detailed metrics endpoint for monitoring and alerting.
        """
        ...
