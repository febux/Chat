"""
Message API routes for the application.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from src.backend.app.providers.centrifugo.provider_v1 import \
    get_centrifugo_api_service
from src.backend.app.providers.message.provider_v1 import \
    get_message_api_service
from src.backend.app.services.centrifugo.meta import CentrifugoServiceMeta
from src.backend.app.services.message.meta import MessageServiceMeta
from src.backend.app.utils.current_user import get_current_user
from src.backend.middleware.rate_limit_middleware import default_limiter
from src.backend.schemas.messages.message_create import ChannelMessageCreate
from src.backend.schemas.messages.message_get import Message
from src.backend.schemas.messages.message_list import MessageList
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
    if not await service.is_channel_member(channel_id, current_user.id):
        raise HTTPException(status_code=403, detail="User is not a member of this channel")
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
@default_limiter.limit("30/minute")
async def send_message(
    request: Request,
    message: ChannelMessageCreate,
    service: Annotated[MessageServiceMeta, Depends(get_message_api_service)],
    centrifugo_service: Annotated[CentrifugoServiceMeta, Depends(get_centrifugo_api_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not await service.is_channel_member(message.channel_id, current_user.id):
        raise HTTPException(status_code=403, detail="User is not a member of this channel")
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


@router.delete("/{message_id}", response_model=dict)
async def delete_message(
    message_id: UUID,
    service: Annotated[MessageServiceMeta, Depends(get_message_api_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Soft-delete a message.

    Only the message's sender may delete it. A failure (message missing,
    already deleted, or owned by someone else) is uniformly reported as 403 so
    the endpoint cannot be used to enumerate message ids or infer ownership.

    :param message_id: ID of the message to delete.
    :param current_user: The authenticated user (must be the sender).
    """
    deleted = await service.delete_message(message_id=message_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=403, detail="Cannot delete this message")
    return JSONResponse(status_code=200, content={"detail": "Message deleted"})
