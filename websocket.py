from fastapi import WebSocket, WebSocketDisconnect
import asyncio
from typing import List, Dict
import json
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.current_count: int = 0

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send current count immediately upon connection
        await self.send_count_to_client(websocket, self.current_count)

    async def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def broadcast_count(self, count: int):
        self.current_count = count
        for connection in self.active_connections:
            try:
                await self.send_count_to_client(connection, count)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                await self.disconnect(connection)

    async def send_count_to_client(self, websocket: WebSocket, count: int):
        try:
            await websocket.send_json({"type": "count_update", "count": count})
        except Exception as e:
            print(f"Error sending to client: {e}")
            await self.disconnect(websocket)

manager = ConnectionManager()

# List to store connected WebSocket clients
connected_clients = []

# Notify clients of new row count
async def notify_clients(count: int):
    await manager.broadcast_count(count)