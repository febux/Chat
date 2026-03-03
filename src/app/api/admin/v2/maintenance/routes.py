"""
Common API routes for the application.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from src.app.providers.base.provider_v2 import get_service_api_service
from src.app.services.base.meta import BaseApiServiceMeta

router = APIRouter()


@router.get(
    "/healthcheck",
    description="Service health check",
    status_code=status.HTTP_200_OK,
)
async def service_healthcheck(
    request: Request,
    service: Annotated[BaseApiServiceMeta, Depends(get_service_api_service)],
) -> Response:
    """
    Service health check endpoint.

    This endpoint is used to verify the availability and health of the service.
    It returns a simple "OK" response if the service is running and healthy.

    :return: statuses indicating the health of the API service and connected services.
    """
    return await service.healthcheck(request)


@router.get(
    "/metrics",
    description="Service metrics",
    status_code=status.HTTP_200_OK,
)
async def service_metrics(
    request: Request,
    service: Annotated[BaseApiServiceMeta, Depends(get_service_api_service)],
) -> Response:
    """
    Service metrics endpoint.

    This endpoint is used to retrieve detailed metrics
    about the service, such as CPU usage, memory usage, and active connections.

    :return: metrics for the API service and connected services.
    """
    return await service.system_metrics(request)
