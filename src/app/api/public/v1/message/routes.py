"""
Message API routes for the application.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse

from src.schemas.messages.message_get import Message
from src.schemas.messages.message_list import MessageList
from src.core.websocket.redis_socketio_manager import ConnectionManager
from src.app.providers.message.provider_v1 import get_message_api_service
from src.app.services.message.meta import MessageServiceMeta
from src.app.utils.current_user import get_current_user
from src.schemas.messages.message_create import MessageCreate
from src.schemas.users.user_get import User

router = APIRouter()


@router.get("/{user_id}", response_model=MessageList)
async def get_messages(
    request: Request,
    user_id: UUID,
    service: Annotated[MessageServiceMeta, Depends(get_message_api_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(30, ge=1, le=100),
    before_id: UUID | None = None,  # Скролл вверх по истории
):
    messages = await service.get_messages_between_users(
        recipient_id=user_id,
        sender_id=current_user.id,
        limit=limit,
        before_id=before_id,
    )
    return MessageList(
        messages=[
            Message(
                id=m.id,
                sender_id=m.sender_id,
                recipient_id=m.recipient_id,
                content=m.content,
                created_at=m.created_at.isoformat(),
            ) for m in messages
        ],
        has_more=len(messages) == limit,
        next_before_id=messages[0].id if messages else None
    )


@router.post("", response_model=MessageCreate)
async def send_message(
    request: Request,
    message: MessageCreate,
    service: Annotated[MessageServiceMeta, Depends(get_message_api_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    await service.create(
        sender_id=current_user.id,
        content=message.content,
        recipient_id=message.recipient_id,
    )

    return JSONResponse(
        status_code=201,
        content={"message": "Message sent successfully"}
    )
