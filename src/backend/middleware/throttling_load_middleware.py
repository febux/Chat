"""
Lightweight load balancer middleware for FastAPI.

This middleware adds a simple load balancing mechanism to distribute incoming requests across multiple FastAPI instances.
"""

import asyncio

from fastapi.requests import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.backend.core.logger import AppLogger

# Create a semaphore for limiting concurrent requests to the load balancer.
gate = asyncio.Semaphore(400)  # tune to latency target


class ThrottlingLoadMiddleware(BaseHTTPMiddleware):
    """
    Middleware for FastAPI that implements a simple load balancing mechanism.
    """

    def __init__(self, app: ASGIApp, logger: AppLogger) -> None:
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        """
        Dispatches the incoming request and adds a simple load balancing mechanism.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: The outgoing response object.
        """
        if not gate.locked() and gate._value == 0:
            return JSONResponse({"message": "Service is busy"}, status_code=503)
        async with gate:
            return await call_next(request)
