from fastapi import WebSocket, WebSocketDisconnect
import asyncio

# List to store connected WebSocket clients
connected_clients = []

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        while True:
            await asyncio.sleep(3600)  # Keep the connection alive
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

# Notify clients of new row count
async def notify_clients(count: int):
    for client in connected_clients:
        try:
            await client.send_json({"count": count})
        except:
            connected_clients.remove(client)
