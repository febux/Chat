"""
Native Python code for managing WebSocket connections.
"""

from starlette.websockets import WebSocket


class ConnectionManager:
    """
    Manages active WebSocket connections and provides methods for sending messages to connected clients.

    Vars:
        active_connections (list[WebSocket]): A list of active WebSocket connections.
    """

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Accepts a new WebSocket connection and adds it to the active connections.

        :param websocket: The WebSocket connection to accept.
        :return: None
        """
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """
        Removes a WebSocket connection from the active connections.

        :param websocket: The WebSocket connection to remove.
        :return: None
        """
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Sends a personal message to a specific WebSocket connection.

        :param message: The message to send.
        :param websocket: The WebSocket connection to send the message to.
        """
        await websocket.send_text(message)

    async def send_json_message(self, message: str, websocket: WebSocket):
        """
        Sends a JSON message to a specific WebSocket connection.

        :param message: The message to send.
        :param websocket: The WebSocket connection to send the message to.
        """
        await websocket.send_json(message)

    async def broadcast(self, message: str):
        """
        Broadcasts a message to all active WebSocket connections.

        :param message: The message to broadcast.
        """
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()
