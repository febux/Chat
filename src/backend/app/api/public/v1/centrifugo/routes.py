from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from src.backend.app.providers.centrifugo.provider_v1 import get_centrifugo_api_service
from src.backend.app.services.centrifugo.meta import CentrifugoServiceMeta
from src.backend.app.utils.current_user import get_current_user
from src.backend.schemas.users.user_get import User

router = APIRouter(tags=["centrifugo"])

class ChannelTokenRequest(BaseModel):
    channel_id: UUID


@router.get("/token")
async def get_centrifugo_token(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CentrifugoServiceMeta, Depends(get_centrifugo_api_service)],
):
    token = await service.create_centrifugo_token(current_user.id)
    return {"token": token}


@router.post("/subscription-token")
async def get_subscription_token(
    body: ChannelTokenRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CentrifugoServiceMeta, Depends(get_centrifugo_api_service)],
):
    token = await service.create_subscription_token(current_user.id, body.channel_id)
    return {"token": token}
