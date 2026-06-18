"""
Centrifugo service implementation.
"""

from uuid import UUID

import httpx

from src.backend.app.utils.auth import (create_centrifugo_token,
                                        create_subscription_token)
from src.backend.config.main import settings
from src.backend.core.logger.logger_factory import logger_bind
from src.backend.database.sqlalchemy.orm_manager import RepositoryManagerMeta

_centrifugo_client: httpx.AsyncClient | None = None


async def get_centrifugo_http_client() -> httpx.AsyncClient:
    """
    Return the process-wide shared Centrifugo HTTP client.

    Creating an ``httpx.AsyncClient`` per publish re-opens a TCP/TLS connection on
    every message, which is wasteful on the send hot path. The client is created
    lazily and reused; :func:`close_centrifugo_http_client` should be called on
    application shutdown (wired in the app lifespan).

    :return: A shared ``httpx.AsyncClient`` instance.
    """
    global _centrifugo_client
    if _centrifugo_client is None:
        _centrifugo_client = httpx.AsyncClient(
            base_url=settings.app.centrifugo_http_url,
            timeout=5.0,
            http2=True,
        )
    return _centrifugo_client


async def close_centrifugo_http_client() -> None:
    """
    Close the shared Centrifugo HTTP client, if one was opened.

    Intended to be called from the application lifespan shutdown handler.
    """
    global _centrifugo_client
    if _centrifugo_client is not None:
        await _centrifugo_client.aclose()
        _centrifugo_client = None


class CentrifugoService:
    """
    A service class for handling Centrifugo operations.
    """

    def __init__(
        self,
        orm_manager: RepositoryManagerMeta,
    ):
        self.orm_manager = orm_manager
        self.logger = logger_bind("CentrifugoService")

    async def create_centrifugo_token(
        self,
        user_id: UUID,
    ) -> str:
        """
        Create a Centrifugo token for a given user ID.

        :param user_id: The ID of the user.
        :return: The Centrifugo token.
        """
        return create_centrifugo_token(str(user_id))

    async def publish_to_channel(
        self,
        channel_id: UUID,
        message: "Message",     # type: ignore[arg-value]
    ) -> None:
        """
        Publish a payload to a specific channel.

        Delivery is best-effort: the message has already been persisted to the
        database by the caller, so a transient Centrifugo failure is logged rather
        than propagated (it must not turn a successful send into a 500). The HTTP
        client is reused across publishes via :func:`get_centrifugo_http_client`.

        :param channel_id: The ID of the channel.
        :param message: The payload to be published.
        :return: None
        """
        payload = {
            "content": message.content,
            "id": str(message.id),
            "temp_id": None,
            "sender_id": str(message.sender_id),
            "channel_id": str(message.channel_id),
            "created_at": message.created_at.isoformat(),
        }
        self.logger.info(f"Publishing payload to channel {channel_id}: {message.content}", payload=payload)
        client = await get_centrifugo_http_client()
        try:
            res = await client.post(
                "/api/publish",
                headers={"X-API-Key": settings.app.CENTRIFUGO_HTTP_API_KEY},
                json={
                    "channel": f"chat:{channel_id}",
                    "data": payload
                },
            )
            res.raise_for_status()
        except httpx.HTTPError as exc:
            self.logger.error(f"Failed to publish message to channel {channel_id}: {exc}")

    async def create_subscription_token(
        self,
        user_id: UUID,
        channel_id: UUID,
    ) -> str:
        """
        Create a subscription token for a given user ID and channel ID.

        :param user_id: The ID of the user.
        :param channel_id: The ID of the channel.
        :return: None
        """
        return create_subscription_token(str(user_id), str(channel_id))
