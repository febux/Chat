"""
Websocket manager using FastAPI-SocketIO.
"""

from typing import Any

from fastapi_socketio import SocketManager


class ConnectionManager:
    """
    Manages active WebSocket connections using FastAPI-SocketIO.

    Attributes:
        sio (SocketManager): FastAPI-SocketIO instance.
    Vars:
        active_connections (dict[str, any]): Map of sid to user_info/username/etc.
    """

    def __init__(self, socketio: SocketManager):
        self.sio = socketio
        self.active_connections = {}  # sid: user_info/username/etc.

    async def connect(self, sid: str, user_info: Any = None):
        """
        Connects a WebSocket client to the server and stores their user information.

        :param sid: Socket ID of the connected client.
        :param user_info: User information for the connected client.
        :return: None
        """
        self.active_connections[sid] = user_info

    async def disconnect(self, sid: str):
        """
        Disconnects a WebSocket client from the server and removes their user information.

        :param sid: Socket ID of the disconnected client.
        :return: None
        """
        if sid in self.active_connections:
            del self.active_connections[sid]

    async def send_personal_message(self, message: str, sid: str):
        """
        Sends a personal message to a specific WebSocket client.

        :param message: The message to send.
        :param sid: Socket ID of the recipient client.
        :return: None
        """
        await self.sio.emit("personal_message", message, room=sid)

    async def send_json_message(self, message: str, sid: str):
        """
        Sends a JSON message to a specific WebSocket client.

        :param message: The JSON message to send.
        :param sid: Socket ID of the recipient client.
        :return: None
        """
        await self.sio.emit("json_message", message, room=sid)

    async def broadcast(self, message: str):
        """
        Broadcasts a message to all connected WebSocket clients.

        :param message: The message to broadcast.
        :return: None
        """
        await self.sio.emit("broadcast", message)

    def get_active_connections(self):
        """
        Returns a list of active WebSocket client Socket IDs.

        :return: List of active WebSocket client Socket IDs.
        """
        return list(self.active_connections.keys())
