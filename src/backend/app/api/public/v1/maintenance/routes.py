"""
Common API routes for the application.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from src.backend.app.providers.base.provider_v1 import get_service_api_service
from src.backend.app.services.base.meta import BaseApiServiceMeta

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
