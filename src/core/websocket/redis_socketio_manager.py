"""
Websocket manager using FastAPI-SocketIO with Redis scaling support.
"""
from datetime import datetime, UTC
from enum import Enum
from typing import Any

import socketio
from fastapi import FastAPI, HTTPException
from jose import jwt, JWTError, ExpiredSignatureError
from jwt import InvalidTokenError

from src.config.main import settings
from src.core.logger.logger_factory import logger_bind

logger = logger_bind("RedisSocketIOManager")

class SocketEvent(Enum):
    CHAT_MESSAGE = "chat_message"
    JSON_MESSAGE = "json_message"
    PERSONAL_MESSAGE = "personal_message"
    SYSTEM_MESSAGE = "system_message"
    SEND_MESSAGE = "send_message"
    PRIVATE_MESSAGE = "private_message"
    TYPING = "typing"
    ROOM_MESSAGE = "room_message"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    ERROR = "error"


class ConnectionManager:
    """
    Manages active WebSocket connections using FastAPI-SocketIO,
    with Redis-based scaling support for multi-instance environments.

    Attributes:
        sio (SocketManager): FastAPI-SocketIO instance connected via Redis.

    Vars:
        active_connections (dict[str, Any]): Map of sid to user_info/username/etc.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        """
        Initializes the WebSocket manager with Redis message queue support.

        :param redis_url: Redis connection URL (default: redis://localhost:6379/0).
        :return: None
        """
        redis_manager = None
        if redis_url:
            redis_manager = socketio.AsyncRedisManager(
                url=redis_url,
                logger=logger,
            )

        self.sio = socketio.AsyncServer(
            client_manager=redis_manager,
            async_mode="asgi",
            async_handlers=True,
            cors_allowed_origins=["*"],
            ping_timeout=60,
            ping_interval=30,
            logger=True,
            engineio_logger=True,
        )

        # sid → user_info
        self.active_connections: dict[str, Any] = {}

        # user_id → sid
        self.user_sessions: dict[str, str] = {}

        # Register built-in socket event handlers
        self._register_handlers()

    def mount_to_app(self, app: FastAPI, path: str = "/socket.io"):
        """
        Mounts the WebSocket manager to the FastAPI app.

        :param app: FastAPI app instance.
        :param path: Path to mount the WebSocket manager at (default: "/socket.io").
        :return: None
        """
        app.mount(path, socketio.ASGIApp(socketio_server=self.sio, socketio_path=path))
        logger.debug(f"WebSocket manager mounted at {path=}")

        app.state.socket_manager = self

    async def _validate_jwt_token(self, token: str) -> str:
        """
        Validates and retrieves user ID from a JWT token.

        :param token: JWT token.
        :return: User ID.
        """
        try:
            payload = jwt.decode(token, settings.app.JWT_SECRET_KEY, algorithms=settings.app.JWT_ALGORITHM)

            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token payload")

            return str(user_id)

        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(status_code=401, detail="Token validation failed")

    def _register_handlers(self):
        @self.sio.on("connect")
        async def connect(sid, environ, auth):
            """
            Called on new WebSocket connection.
            Performs token-based authentication if provided.
            """
            cookie_header = environ.get('HTTP_COOKIE', '')
            logger.debug(f"[ws][cookies] {cookie_header}")

            # Парсим куки
            cookies = {}
            for cookie in cookie_header.split(';'):
                if '=' in cookie:
                    key, value = cookie.strip().split('=', 1)
                    cookies[key] = value

            token = cookies.get('users_access_token')
            logger.debug(f"[ws][token] {token=}")
            user_id = await self._validate_jwt_token(token)
            user_info = {
                "username": f"user_{sid[-4:]}",
                "token": token,
                "user_id": user_id,
            }
            self.active_connections[sid] = user_info
            self.user_sessions[str(user_id)] = sid  # маппинг по user_id, не username
            await self.broadcast("user_connected", {
                "user_id": user_id,
                "username": user_info["username"],
                "timestamp": datetime.now(UTC).isoformat()
            })
            logger.debug(f"[ws][connect] {sid=} user={user_info}")
            await self.sio.emit("system_message", f"Welcome, {user_info['username']}!", room=sid)

        @self.sio.on("disconnect")
        async def disconnect(sid):
            """
            Triggered when client disconnects.
            """
            user_info = self.active_connections.pop(sid, None)
            if user_info:
                user_id = user_info["user_id"]
                self.user_sessions.pop(user_id, None)

                await self.broadcast("user_disconnected", {
                    "user_id": user_id,
                    "username": user_info.get("username"),
                    "timestamp": datetime.now(UTC).isoformat()
                })

                logger.info(f"[ws][disconnect] user_id={user_id} sid={sid}")
            await self.broadcast("system_message", f"{user_info['username']} left." if user_info else "A user left.")

        # --------------------------------------------------------------------------
        # Chat and messaging events
        # --------------------------------------------------------------------------

        @self.sio.on(SocketEvent.CHAT_MESSAGE.value)
        async def handle_message(sid, data):
            """
            Handles a simple text chat message and broadcasts it to all users.
            """
            user_info = self.active_connections.get(sid)
            username = user_info.get("username", "Unknown") if user_info else "Anonymous"

            logger.debug(f"[ws][message] {sid=} {username=}: {data}")
            await self.broadcast("chat_message", f"{username}: {data}")

        @self.sio.on(SocketEvent.PRIVATE_MESSAGE.value)
        async def handle_private_message(sid, data):
            """
            Sends a private message to a specific user.

            data example:
                {"to": "user_1234", "content": "Hello!"}
            """
            user_info = self.active_connections.get(sid)
            sender = user_info.get("username", "Anonymous") if user_info else "Anonymous"

            target = data.get("to")
            content = data.get("content")

            if not target or not content:
                await self.sio.emit("error", "Invalid private message format", room=sid)
                return

            target_sid = self.user_sessions.get(target)
            if not target_sid:
                await self.sio.emit("error", f"User {target} not connected", room=sid)
                return

            await self.send_personal_message(content, sid=target_sid)
            await self.send_personal_message(content, sid=sid)

            logger.debug(f"[ws][private_message] {sender} → {target}: {content}")

        @self.sio.on(SocketEvent.JSON_MESSAGE.value)
        async def handle_json_message(sid, data):
            """
            Handles a JSON message and broadcasts it to all users in a specific room.
            """
            user_info = self.active_connections.get(sid)
            sender = user_info.get("username", "Anonymous") if user_info else "Anonymous"

            target = data.get("to")
            content = data.get("content")

            if not target or not content:
                await self.sio.emit("error", "Invalid private message format", room=sid)
                return

            target_sid = self.user_sessions.get(target)
            if not target_sid:
                await self.sio.emit("error", f"User {target} not connected", room=sid)
                return

            await self.send_json_message(content, sid=target_sid)
            await self.send_json_message(content, sid=sid)

            logger.debug(f"[ws][private_message] {sender} → {target}: {content}")

        @self.sio.on(SocketEvent.TYPING.value)
        async def handle_typing(sid, data):
            """
            Informs others that a user is typing.
            """
            user_info = self.active_connections.get(sid)
            username = user_info.get("username", "Unknown") if user_info else "Anonymous"
            user_id = user_info.get("user_id")  # нужно хранить при connect
            await self.broadcast("typing", {"username": username, "user_id": user_id, **data})

        # --------------------------------------------------------------------------
        # Rooms (channels) management
        # --------------------------------------------------------------------------
        @self.sio.on(SocketEvent.JOIN_ROOM.value)
        async def join_room(sid, data):
            """
            Adds a client to a room (channel).

            data example:
                {"room": "lobby"}
            """
            room = data.get("room")
            if not room:
                await self.sio.emit("error", "Missing room name", room=sid)
                return

            await self.sio.enter_room(sid, room)
            user = self.active_connections.get(sid, {}).get("username", sid)
            logger.debug(f"[ws][join_room] {user} joined {room}")
            await self.sio.emit("system_message", f"{user} joined {room}", room=room)

        @self.sio.on(SocketEvent.LEAVE_ROOM.value)
        async def leave_room(sid, data):
            """
            Removes a client from a room.

            data example:
                {"room": "lobby"}
            """
            room = data.get("room")
            if not room:
                return

            await self.sio.leave_room(sid, room)
            user = self.active_connections.get(sid, {}).get("username", sid)
            logger.debug(f"[ws][leave_room] {user} left {room}")
            await self.sio.emit("system_message", f"{user} left {room}", room=room)

        @self.sio.on(SocketEvent.ROOM_MESSAGE.value)
        async def handle_room_message(sid, data):
            """
            Sends a message to all users in a specific room.

            data example:
                {"room": "lobby", "message": "Hello everyone!"}
            """
            room = data.get("room")
            message = data.get("message")

            if not room or not message:
                await self.sio.emit("error", "Invalid room message", room=sid)
                return

            user_info = self.active_connections.get(sid)
            username = user_info.get("username", "Unknown") if user_info else "Anonymous"
            await self.sio.emit("room_message", f"{username}: {message}", room=room)
            logger.debug(f"[ws][room_message] {username} → {room}: {message}")

    async def connect(self, sid: str, user_info: Any = None):
        """
        Registers a new WebSocket connection manually (optional).

        :param sid: Socket ID of the connected client.
        :param user_info: Additional user information.
        :return: None
        """
        self.active_connections[sid] = user_info

    async def disconnect(self, sid: str):
        """
        Removes a WebSocket client from the active pool.

        :param sid: Socket ID.
        :return: None
        """
        self.active_connections.pop(sid, None)

    async def send_to_user(self, user_id: str, event: str, data: dict):
        """
        Sends a message to a specific WebSocket client.

        Works across multiple server instances via Redis pub/sub if configured.

        :param user_id: The user ID to send the message to.
        :param event: The event type (e.g., "chat_message", "typing").
        :param data: The message data.
        :return: None
        """
        sid = self.user_sessions.get(user_id)
        if sid:
            await self.sio.emit(event, data, room=sid)
            logger.debug(f"[ws][send_to_user] {user_id} → {event}")
        else:
            logger.warning(f"[ws][send_to_user] User {user_id} not connected")

    async def send_personal_message(self, message: str, sid: str):
        """
        Sends a personal message to a specific WebSocket client.

        Works across multiple server instances via Redis pub/sub if configured.

        :param message: The message to send.
        :param sid: Socket ID of the recipient.
        :return: None
        """
        await self.sio.emit("personal_message", message, room=sid)

    async def send_json_message(self, message: dict, sid: str):
        """
        Sends a JSON message to a specific WebSocket client.

        :param message: The JSON message to send.
        :param sid: Socket ID of the recipient.
        :return: None
        """
        await self.sio.emit("json_message", message, room=sid)

    async def broadcast(self, event: str, message: Any):
        """
        Broadcasts a message to all connected clients.
        If using Redis, broadcasts across all instances.

        :param event: The event name.
        :param message: The message to broadcast.
        :return: None
        """
        await self.sio.emit(event, message)

    async def join_channel(self, sid: str, channel_id: str):
        """
        Adds a client to a channel.

        :param sid: Socket ID of the connected client.
        :param channel_id: The channel ID to join.
        :return: None
        """
        room = f"channel:{channel_id}"
        await self.sio.enter_room(sid, room)
        logger.debug(f"[ws][join_channel] sid={sid} joined {room}")

    async def leave_channel(self, sid: str, channel_id: str):
        """
        Removes a client from a channel.

        :param sid: Socket ID of the connected client.
        :param channel_id: The channel ID to leave.
        :return: None
        """
        room = f"channel:{channel_id}"
        await self.sio.leave_room(sid, room)
        logger.debug(f"[ws][leave_channel] sid={sid} left {room}")

    async def broadcast_to_channel(self, channel_id: str, event: str, data: dict):
        """
        Broadcasts a message to all users in a specific channel.

        :param channel_id: The channel ID.
        :param event: The event type (e.g., "chat_message", "typing").
        :param data: The message data.
        :return: None
        """
        room = f"channel:{channel_id}"
        await self.sio.emit(event, data, room=room)

    def get_active_connections(self):
        """
        Returns a list of active Socket IDs (local instance only).

        :return: List of active WebSocket client Socket IDs.
        """
        return list(self.active_connections.keys())

    def get_online_users(self):
        """
        Returns a list of active users with their usernames (local instance only).

        :return: List of active user information dictionaries.
        """
        return [
            {
                "user_id": info["user_id"],
                "username": info.get("username")
            }
            for info in self.active_connections.values()
        ]
