"""
Redis client for managing WebSocket connections and broadcasting messages.
"""

import asyncio
from typing import Dict, List

import orjson
from fastapi import WebSocket

from src.backend.core.redis.client import RedisClient


class ConnectionManager:
    """
    Manages active WebSocket connections and broadcasts messages to connected clients.

    The manager allows you to monitor active WebSocket sessions, send personal and broadcast messages,
    and if Redis is available, synchronize messages between several application instances.


    Attributes:
        redis_client (RedisClient | None):
            An optional Redis client for broadcasting messages.

    Vars:
        active_connections (Dict[str, List[WebSocket]]):
            A dictionary of user IDs to WebSocket connections.
        redis_sub (PubSub | None):
            An optional Redis subscriber for listening to broadcast messages.
        _listener_task (Task | None):
            An optional task for listening to Redis messages.


    Usage:
    >>> @app.websocket("/ws/{user_id}")
        ... async def websocket_endpoint(websocket: WebSocket, user_id: str):
        ...     await manager.connect(websocket, user_id)
        ...     try:
        ...         while True:
        ...             data = await websocket.receive_text()
        ...             await manager.send_personal_message(f"ECHO: {data}", user_id)
        ...             await manager.broadcast(f"Broadcast from {user_id}: {data}")
        ...     except WebSocketDisconnect:
        ...         manager.disconnect(websocket, user_id)
    """

    def __init__(self, redis_client: RedisClient | None = None):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis_client = redis_client
        self.redis_sub = None
        self._listener_task = None

    async def startup(self):
        """
        Initializes the connection manager and starts listening to Redis messages.

        :return: None
        """
        if self.redis_client:
            self.redis_sub = self.redis_client.client.pubsub()
            channels = ["broadcast"]
            for user_id in self.active_connections.keys():
                channels.append(f"user:{user_id}")
            await self.redis_sub.subscribe(*channels)
            self._listener_task = asyncio.create_task(self._redis_listener())

    async def _redis_listener(self):
        """
        Listens to Redis messages and broadcasts them to connected clients.

        :return: None
        """
        if not self.redis_sub:
            raise ValueError("Redis client not initialized")

        async for message in self.redis_sub.listen():
            if message["type"] != "message":
                continue
            channel = message["channel"]
            data = message["data"]
            if channel == "broadcast":
                for conns in self.active_connections.values():
                    for ws in conns:
                        await ws.send_text(data)
            elif channel.startswith("user:"):
                user_id = channel.split(":", 1)[1]
                if user_id in self.active_connections:
                    for ws in self.active_connections[user_id]:
                        await ws.send_text(data)

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Adds a WebSocket connection to the active connections and subscribes to the user's channel.

        :param websocket: The WebSocket connection.
        :param user_id: The user ID for the connection.
        :return: None
        """
        await websocket.accept()
        conns = self.active_connections.setdefault(user_id, [])
        conns.append(websocket)
        if self.redis_sub:
            await self.redis_sub.subscribe(f"user:{user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        """
        Removes a WebSocket connection from the active connections and unsubscribes from the user's channel.

        :param websocket: The WebSocket connection.
        :param user_id: The user ID for the connection.
        :return: None
        """
        conns = self.active_connections.get(user_id)
        if conns and websocket in conns:
            conns.remove(websocket)
        if conns == []:
            self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: str, user_id: str):
        """
        Sends a personal message to a specific user.

        :param message: The message to send.
        :param user_id: The user ID to send the message to.
        :return: None
        """
        if self.redis_client:
            await self.redis_client.client.publish(f"user:{user_id}", message)
        else:
            for ws in self.active_connections.get(user_id, []):
                await ws.send_text(message)

    async def send_json_message(self, message: dict, user_id: str, *, mode: str = "text"):
        """
        Sends a JSON message to a specific user.

        :param message: The JSON message to send.
        :param user_id: The user ID to send the message to.
        :param mode: The mode for sending the JSON message ("text" or "binary").
        :return: None
        """
        if self.redis_client:
            await self.redis_client.client.publish(f"user:{user_id}", orjson.dumps(message))
        else:
            for ws in self.active_connections.get(user_id, []):
                await ws.send_json(message, mode)

    async def broadcast(self, message: str):
        """
        Broadcasts a message to all connected clients.

        :param message: The message to broadcast.
        :return: None
        """
        if self.redis_client:
            await self.redis_client.client.publish("broadcast", message)
        else:
            for conns in self.active_connections.values():
                for ws in conns:
                    await ws.send_text(message)
