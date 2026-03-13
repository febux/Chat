"""
Message API routes for the application.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse

from src.backend.app.providers.centrifugo.provider_v1 import get_centrifugo_api_service
from src.backend.app.services.centrifugo.meta import CentrifugoServiceMeta
from src.backend.app.utils.current_user import get_current_user
from src.backend.schemas.messages.message_get import Message
from src.backend.schemas.messages.message_list import MessageList
from src.backend.app.providers.message.provider_v1 import get_message_api_service
from src.backend.app.services.message.meta import MessageServiceMeta
from src.backend.schemas.messages.message_create import ChannelMessageCreate
from src.backend.schemas.users.user_get import User

router = APIRouter(tags=["message"])


@router.get("/{channel_id}", response_model=MessageList)
async def get_channel_messages(
    channel_id: UUID,
    service: Annotated[MessageServiceMeta, Depends(get_message_api_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(30, ge=1, le=100),
    before_id: UUID | None = None,
) -> MessageList:
    # опционально: проверить, что current_user состоит в канале
    messages = await service.get_messages_for_channel(
        channel_id=channel_id,
        limit=limit,
        before_id=before_id,
    )

    return MessageList(
        messages=[
            Message(
                id=m.id,
                sender_id=m.sender_id,
                channel_id=channel_id,
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
        has_more=len(messages) == limit,
        next_before_id=messages[0].id if messages else None,
    )


@router.post("", response_model=dict)
async def send_message(
    request: Request,
    message: ChannelMessageCreate,
    service: Annotated[MessageServiceMeta, Depends(get_message_api_service)],
    centrifugo_service: Annotated[CentrifugoServiceMeta, Depends(get_centrifugo_api_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    message = await service.create(
        sender_id=current_user.id,
        content=message.content,
        channel_id=message.channel_id,
    )
    await centrifugo_service.publish_to_channel(
        channel_id=message.channel_id,
        message=message,
    )

    return JSONResponse(
        status_code=201,
        content={"message": "Message was saved successfully"}
    )
