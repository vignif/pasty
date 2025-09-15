
"""
websocket.py

Manages WebSocket connections for real-time row count updates in Pasty.
"""

from fastapi import WebSocket
from typing import List


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts row count updates."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.current_count: int = 0

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send current count immediately upon connection
        await self.send_count_to_client(websocket, self.current_count)

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection from the active list."""
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def broadcast_count(self, count: int):
        """Broadcast the current row count to all active connections."""
        self.current_count = count
        for connection in self.active_connections:
            try:
                await self.send_count_to_client(connection, count)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                await self.disconnect(connection)

    async def send_count_to_client(self, websocket: WebSocket, count: int):
        """Send the row count to a specific WebSocket client."""
        try:
            await websocket.send_json({"type": "count_update", "count": count})
        except Exception as e:
            print(f"Error sending to client: {e}")
            await self.disconnect(websocket)


manager = ConnectionManager()


# List to store connected WebSocket clients (legacy, not used)
connected_clients = []

async def notify_clients(count: int):
    """Notify all clients of a new row count."""
    await manager.broadcast_count(count)