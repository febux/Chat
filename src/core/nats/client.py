"""
NATS client using asyncio for asynchronous NATS operations.
"""

import asyncio
from typing import Any, Callable, Awaitable

from nats.aio.client import Client as NATS
from nats.errors import ConnectionClosedError, TimeoutError, NoServersError

from src.core.logger.logger_factory import logger_bind

logger = logger_bind("NATSClient")


class NATSClient:
    """
    A client for interacting with a NATS server using asyncio.
    """

    def __init__(self, nats_url: str, reconnect: bool = True) -> None:
        """
        Initialize the NATS client.

        :param nats_url: NATS server URL.
        :param reconnect: Whether to automatically attempt reconnects.
        """
        self.nats_url = str(nats_url)
        self.reconnect = reconnect
        self._client = NATS()

    @property
    def client(self) -> NATS:
        """Return the internal NATS client instance."""
        return self._client

    async def connect(self) -> None:
        """
        Connect to the NATS server asynchronously.
        """
        logger.debug(f"Connecting to NATS server: {self.nats_url}")
        try:
            await self._client.connect(
                servers=[self.nats_url],
                max_reconnect_attempts=10,
                reconnect_time_wait=2,
                allow_reconnect=self.reconnect,
                ping_interval=60,
            )
            logger.debug("Successfully connected to NATS.")
        except NoServersError as e:
            logger.error(f"Unable to connect to NATS server: {e}")
            raise

    async def close_connection(self) -> None:
        """
        Close the NATS connection asynchronously.
        """
        if self._client.is_connected:
            logger.info("Closing NATS connection...")
            await self._client.drain()
            await self._client.close()

    async def _reconnect(self) -> None:
        """
        Attempt to reconnect to the NATS server if the connection is lost.
        """
        if not self.reconnect:
            logger.warning("Reconnect is disabled. Skipping reconnect attempt.")
            return
        logger.info("Reconnecting NATS client...")
        try:
            await self.close_connection()
            await self.connect()
        except Exception as e:
            logger.error(f"Error during NATS reconnect: {e}")
            raise

    async def _execute_with_reconnect(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        retries: int = 3,
        delay: float = 1.0,
        **kwargs,
    ) -> Any:
        """
        Execute the specified function with automatic reconnect.

        :param func: The NATS operation coroutine to execute.
        :param retries: Number of retries before giving up.
        :param delay: Delay between retries in seconds.
        """
        last_exc = None
        for attempt in range(retries):
            try:
                return await func(*args, **kwargs)
            except (ConnectionClosedError, TimeoutError) as e:
                last_exc = e
                logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}. Reconnecting...")
                await self._reconnect()
                await asyncio.sleep(delay)
        logger.error(f"Failed to execute function after all retries: {last_exc}")
        raise last_exc or RuntimeError("Unrecoverable error executing NATS command")

    async def publish(self, subject: str, message: bytes) -> None:
        """
        Publish a message to a NATS subject.

        :param subject: The subject name to publish to.
        :param message: The message data as bytes.
        """
        await self._execute_with_reconnect(self._client.publish, subject, message)

    async def subscribe(self, subject: str, queue: str | None = None, cb: Callable[[Any], Awaitable[Any]] | None = None):
        """
        Subscribe to a NATS subject, optionally with a queue group.

        :param subject: The subject name to subscribe to.
        :param queue: Optional queue group name.
        :param cb: Optional async callback for message handling.
        """
        if not cb:
            async def cb(msg):
                logger.info(f"Received message on {msg.subject}: {msg.data.decode()}")
        await self._execute_with_reconnect(self._client.subscribe, subject, queue=queue, cb=cb)

    async def request(self, subject: str, payload: bytes, timeout: float = 2.0) -> bytes | None:
        """
        Send a request and wait for a reply on a NATS subject.

        :param subject: The request subject.
        :param payload: The message payload (bytes).
        :param timeout: Timeout for response.
        :return: The response message data or None.
        """
        msg = await self._execute_with_reconnect(self._client.request, subject, payload, timeout=timeout)
        return msg.data if msg else None


def nats_client_factory(nats_url: str, reconnect: bool = True) -> NATSClient:
    """
    Factory function to create and return a NATS client instance.

    :param nats_url: NATS server URL.
    :param reconnect: Whether to automatically reconnect.
    :return: An instance of NATSClient.
    """
    return NATSClient(nats_url, reconnect=reconnect)
