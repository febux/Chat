from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Body
from starlette.responses import JSONResponse

from src.backend.app.models.enums import ChannelType
from src.backend.schemas.channels.channel_create import ChannelWithMembersCreate
from src.backend.app.providers.channel.provider_v1 import get_channel_api_service
from src.backend.app.services.channel.meta import ChannelServiceMeta
from src.backend.app.utils.current_user import get_current_user
from src.backend.schemas.channels.channel_get import Channel
from src.backend.schemas.users.user_get import User

router = APIRouter(tags=["channels"])


@router.get("", response_model=list[Channel])
async def get_user_channels(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChannelServiceMeta, Depends(get_channel_api_service)],
):
    channels = await service.get_user_channels(user_id=current_user.id)
    return [
        Channel(
            id=ch.id,
            type=ch.type,
            title=ch.title,
            created_by=ch.created_by,
            created_at=ch.created_at,
        )
        for ch in channels
    ]


@router.post("/users", response_model=Channel)
async def get_or_create_channel_between_users(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChannelServiceMeta, Depends(get_channel_api_service)],
    user_ids: list[UUID] = Body(min_length=1),  # Принимаем список user_ids
):
    channel = await service.find_channel_between_users(user_ids=user_ids)

    if not channel:
        channel = await service.create_channel_with_members(
            channel_type=ChannelType.DIRECT,
            title=f"Direct channel between {user_ids[0]} and {user_ids[1]}",
            created_by=current_user.id,
            members=user_ids,
        )
        return JSONResponse(content=channel.to_dict(), status_code=201)
    return JSONResponse(content=channel.to_dict(), status_code=200)



@router.post(
    "",
    response_model=Channel,
    status_code=201,
)
async def create_channel(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    channel_data: ChannelWithMembersCreate,
    service: Annotated[ChannelServiceMeta, Depends(get_channel_api_service)],
):
    return await service.create_channel_with_members(
        **channel_data.model_dump(),
    )
