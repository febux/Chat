import json
from datetime import datetime, UTC
from enum import Enum
from typing import Any

import socketio
from fastapi import FastAPI, HTTPException
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from jwt import InvalidTokenError

from src.backend.core.nats.client import NATSClient, nats_client_factory
from src.backend.config.main import settings
from src.backend.core.logger.logger_factory import logger_bind

logger = logger_bind("NatsSocketIOManager")


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
    WebSocket manager using FastAPI-SocketIO + NATS as pub/sub bus.
    """

    def __init__(self, *, nats_url: str) -> None:
        """
        :param nats_url: NATS server URL.
        """
        self.sio = socketio.AsyncServer(
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
        # user_id → sid (локальный инстанс)
        self.user_sessions: dict[str, str] = {}

        # NATS client (обертка с reconnect)
        self._nats_client: NATSClient = nats_client_factory(nats_url=nats_url)

        # Register socket handlers
        self._register_handlers()

    # -----------------------
    # FastAPI integration
    # -----------------------

    def mount_to_app(self, app: FastAPI, path: str = "/socket.io") -> None:
        app.mount(path, socketio.ASGIApp(socketio_server=self.sio, socketio_path=path))
        logger.debug(f"WebSocket manager mounted at {path=}")

        app.state.socket_manager = self

    # -----------------------
    # NATS connect / subscribe
    # -----------------------

    async def connect_nats(self) -> None:
        await self._nats_client.connect()
        logger.debug("[nats] NATS client connected")

        # subject: chat.channel.<channel_id>
        async def channel_cb(msg):
            try:
                subject = msg.subject  # "chat.channel.<channel_id>"
                data = json.loads(msg.data.decode("utf-8"))
                channel_id = subject.split(".")[-1]
                event = data.get("event")
                payload = data.get("data")

                if not event:
                    logger.warning(f"[nats] missing event in payload: {data}")
                    return

                await self._emit_to_channel_local(channel_id, event, payload)
            except Exception as e:
                logger.exception(f"[nats] channel_cb error: {e}")

        await self._nats_client.subscribe("chat.channel.*", cb=channel_cb)

        # subject: chat.user.<user_id>
        async def user_cb(msg):
            try:
                subject = msg.subject  # "chat.user.<user_id>"
                data = json.loads(msg.data.decode("utf-8"))
                user_id = subject.split(".")[-1]
                event = data.get("event")
                payload = data.get("data")

                if not event:
                    logger.warning(f"[nats] missing event in payload: {data}")
                    return

                await self._emit_to_user_local(user_id, event, payload)
            except Exception as e:
                logger.exception(f"[nats] user_cb error: {e}")

        await self._nats_client.subscribe("chat.user.*", cb=user_cb)

        logger.info("[nats] subscriptions initialized")

    async def disconnect_nats(self) -> None:
        # закрываем через обертку
        await self._nats_client.close_connection()
        logger.info("[nats] disconnected")

    # -----------------------
    # JWT
    # -----------------------

    async def _validate_jwt_token(self, token: str) -> str:
        try:
            payload = jwt.decode(
                token,
                settings.app.JWT_SECRET_KEY,
                algorithms=[settings.app.JWT_ALGORITHM],
            )
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token payload")
            return str(user_id)
        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except (InvalidTokenError, JWTError):
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(status_code=401, detail="Token validation failed")

    # -----------------------
    # Socket.IO handlers
    # -----------------------

    def _register_handlers(self) -> None:
        @self.sio.on("connect")
        async def connect(sid, environ, auth):
            cookie_header = environ.get("HTTP_COOKIE", "")
            logger.debug(f"[ws][cookies] {cookie_header}")

            cookies: dict[str, str] = {}
            for cookie in cookie_header.split(";"):
                if "=" in cookie:
                    key, value = cookie.strip().split("=", 1)
                    cookies[key] = value

            token = cookies.get("users_access_token")
            if not token:
                logger.warning("[ws][connect] no token in cookies")
                raise HTTPException(status_code=401, detail="Not authenticated")

            logger.debug(f"[ws][token] {token=}")

            user_id = await self._validate_jwt_token(token)
            user_info = {
                "username": f"user_{sid[-4:]}",
                "token": token,
                "user_id": user_id,
            }

            self.active_connections[sid] = user_info
            self.user_sessions[str(user_id)] = sid

            await self.broadcast_local(
                SocketEvent.SYSTEM_MESSAGE.value,
                {
                    "type": "user_connected",
                    "user_id": user_id,
                    "username": user_info["username"],
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
            logger.debug(f"[ws][connect] {sid=} user={user_info}")
            await self.sio.emit(
                SocketEvent.SYSTEM_MESSAGE.value,
                f"Welcome, {user_info['username']}!",
                room=sid,
            )

        @self.sio.on("disconnect")
        async def disconnect(sid):
            user_info = self.active_connections.pop(sid, None)
            if user_info:
                user_id = user_info["user_id"]
                self.user_sessions.pop(user_id, None)

                await self.broadcast_local(
                    SocketEvent.SYSTEM_MESSAGE.value,
                    {
                        "type": "user_disconnected",
                        "user_id": user_id,
                        "username": user_info.get("username"),
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
                logger.info(f"[ws][disconnect] user_id={user_id} sid={sid}")
            else:
                await self.broadcast_local(
                    SocketEvent.SYSTEM_MESSAGE.value,
                    {"type": "user_left_unknown"},
                )

        # ---------------- Chat and messaging events ----------------

        @self.sio.on(SocketEvent.CHAT_MESSAGE.value)
        async def handle_message(sid, data):
            """
            Простой глобальный чат (можно оставить локальным или позже вынести в отдельный канал).
            """
            user_info = self.active_connections.get(sid)
            username = user_info.get("username", "Unknown") if user_info else "Anonymous"

            logger.debug(f"[ws][message] {sid=} {username=}: {data}")
            await self.broadcast_local(
                SocketEvent.CHAT_MESSAGE.value,
                f"{username}: {data}",
            )

        @self.sio.on(SocketEvent.PRIVATE_MESSAGE.value)
        async def handle_private_message(sid, data):
            """
            Личное сообщение пользователю (через NATS, чтобы работало между инстансами).

            data example:
                {"to": "<user_id>", "content": "Hello!"}
            """
            user_info = self.active_connections.get(sid)
            sender_id = user_info.get("user_id") if user_info else None

            target_user_id = data.get("to")
            content = data.get("content")

            if not target_user_id or not content:
                await self.sio.emit("error", "Invalid private message format", room=sid)
                return

            payload = {
                "sender_id": str(sender_id) if sender_id else None,
                "recipient_id": str(target_user_id),
                "content": content,
                "created_at": datetime.now(UTC).isoformat(),
            }

            # получатель
            await self.send_to_user(
                str(target_user_id),
                SocketEvent.PERSONAL_MESSAGE.value,
                payload,
            )
            # эхо отправителю
            if sender_id:
                await self.send_to_user(
                    str(sender_id),
                    SocketEvent.PERSONAL_MESSAGE.value,
                    payload,
                )

            logger.debug(f"[ws][private_message] {sender_id} → {target_user_id}: {content}")

        @self.sio.on(SocketEvent.JSON_MESSAGE.value)
        async def handle_json_message(sid, data):
            """
            Личный JSON-месседж (структурированный payload) через NATS.
            data example:
                {"to": "<user_id>", "content": {...}}
            """
            user_info = self.active_connections.get(sid)
            sender_id = user_info.get("user_id") if user_info else None

            target_user_id = data.get("to")
            content = data.get("content")

            if not target_user_id or content is None:
                await self.sio.emit("error", "Invalid JSON message format", room=sid)
                return

            payload = {
                "sender_id": str(sender_id) if sender_id else None,
                "recipient_id": str(target_user_id),
                "content": content,
                "created_at": datetime.now(UTC).isoformat(),
            }

            await self.send_to_user(
                str(target_user_id),
                SocketEvent.JSON_MESSAGE.value,
                payload,
            )
            if sender_id:
                await self.send_to_user(
                    str(sender_id),
                    SocketEvent.JSON_MESSAGE.value,
                    payload,
                )

            logger.debug(f"[ws][json_message] {sender_id} → {target_user_id}: {content}")

        @self.sio.on(SocketEvent.TYPING.value)
        async def handle_typing(sid, data):
            """
            Информируем других участников канала, что пользователь печатает.
            Ожидаем, что фронт будет слать { "channel_id": "...", ... }.
            """
            user_info = self.active_connections.get(sid)
            username = user_info.get("username", "Unknown") if user_info else "Anonymous"
            user_id = user_info.get("user_id") if user_info else None

            channel_id = data.get("channel_id")
            payload = {
                "username": username,
                "user_id": str(user_id) if user_id else None,
                **data,
            }

            if channel_id:
                # через NATS в конкретный канал
                await self.broadcast_to_channel(
                    str(channel_id),
                    SocketEvent.TYPING.value,
                    payload,
                )
            else:
                # fallback – локальный broadcast
                await self.broadcast_local(SocketEvent.TYPING.value, payload)

        # ---------------- Rooms (channels) management ----------------

        @self.sio.on(SocketEvent.JOIN_ROOM.value)
        async def join_room(sid, data):
            """
            data example: {"room": "lobby"} или {"room": "channel:<channel_id>"}.
            """
            room = data.get("room")
            if not room:
                await self.sio.emit("error", "Missing room name", room=sid)
                return

            await self.sio.enter_room(sid, room)
            user = self.active_connections.get(sid, {}).get("username", sid)
            logger.debug(f"[ws][join_room] {user} joined {room}")
            await self.sio.emit(
                SocketEvent.SYSTEM_MESSAGE.value,
                f"{user} joined {room}",
                room=room,
            )

        @self.sio.on(SocketEvent.LEAVE_ROOM.value)
        async def leave_room(sid, data):
            room = data.get("room")
            if not room:
                return

            await self.sio.leave_room(sid, room)
            user = self.active_connections.get(sid, {}).get("username", sid)
            logger.debug(f"[ws][leave_room] {user} left {room}")
            await self.sio.emit(
                SocketEvent.SYSTEM_MESSAGE.value,
                f"{user} left {room}",
                room=room,
            )

        @self.sio.on(SocketEvent.ROOM_MESSAGE.value)
        async def handle_room_message(sid, data):
            """
            Сообщение в комнату/канал.
            data example: {"room": "channel:<channel_id>", "message": "Hello everyone!"}
            """
            room = data.get("room")
            message = data.get("message")

            if not room or not message:
                await self.sio.emit("error", "Invalid room message", room=sid)
                return

            user_info = self.active_connections.get(sid)
            username = user_info.get("username", "Unknown") if user_info else "Anonymous"
            text = f"{username}: {message}"

            # если это комната канала – шлём через NATS в канал
            if room.startswith("channel:"):
                channel_id = room.split(":", 1)[1]
                await self.broadcast_to_channel(
                    str(channel_id),
                    SocketEvent.ROOM_MESSAGE.value,
                    {"room": room, "text": text},
                )
            else:
                # обычная локальная комната
                await self.sio.emit(
                    SocketEvent.ROOM_MESSAGE.value,
                    text,
                    room=room,
                )

            logger.debug(f"[ws][room_message] {username} → {room}: {message}")

    # -----------------------
    # Local-only helpers
    # -----------------------

    async def broadcast_local(self, event: str, message: Any) -> None:
        await self.sio.emit(event, message)

    async def _emit_to_channel_local(self, channel_id: str, event: str, data: dict) -> None:
        room = f"channel:{channel_id}"
        await self.sio.emit(event, data, room=room)
        logger.debug(f"[ws][local_emit_channel] {channel_id=} {event=}")

    async def _emit_to_user_local(self, user_id: str, event: str, data: dict) -> None:
        sid = self.user_sessions.get(user_id)
        if not sid:
            logger.debug(f"[ws][local_emit_user] user {user_id} not connected")
            return
        await self.sio.emit(event, data, room=sid)
        logger.debug(f"[ws][local_emit_user] {user_id=} {event=}")

    # -----------------------
    # Public API (через NATS)
    # -----------------------

    async def publish_to_channel(self, channel_id: str, event: str, data: dict) -> None:
        subject = f"chat.channel.{channel_id}"
        payload = json.dumps({"event": event, "data": data}).encode("utf-8")
        await self._nats_client.publish(subject, payload)
        logger.debug(f"[nats][publish_to_channel] {subject=} {event=}")

    async def publish_to_user(self, user_id: str, event: str, data: dict) -> None:
        subject = f"chat.user.{user_id}"
        payload = json.dumps({"event": event, "data": data}).encode("utf-8")
        await self._nats_client.publish(subject, payload)
        logger.debug(f"[nats][publish_to_user] {subject=} {event=}")

    async def send_to_user(self, user_id: str, event: str, data: dict) -> None:
        await self.publish_to_user(user_id, event, data)

    async def broadcast_to_channel(self, channel_id: str, event: str, data: dict) -> None:
        await self.publish_to_channel(channel_id, event, data)

    async def join_channel(self, sid: str, channel_id: str) -> None:
        room = f"channel:{channel_id}"
        await self.sio.enter_room(sid, room)
        logger.debug(f"[ws][join_channel] sid={sid} joined {room}")

    async def leave_channel(self, sid: str, channel_id: str) -> None:
        room = f"channel:{channel_id}"
        await self.sio.leave_room(sid, room)
        logger.debug(f"[ws][leave_channel] sid={sid} left {room}")

    def get_active_connections(self) -> list[str]:
        return list(self.active_connections.keys())

    def get_online_users(self) -> list[dict[str, Any]]:
        return [
            {"user_id": info["user_id"], "username": info.get("username")}
            for info in self.active_connections.values()
        ]
