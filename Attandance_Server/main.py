"""
Application entry point for the MasterKey server.

Creates the FastAPI app, includes the HTTP routes, and defines the /ws
WebSocket endpoint used by MasterKey Desktop computers to maintain a
live connection with the server.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import database
import devices
from routes import router

app = FastAPI(title="MasterKey Server")

app.include_router(router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.initialize_database()
    yield


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Flow:
    1. Desktop connects.
    2. Desktop sends its device_id as the first message to identify itself.
    3. Server associates this WebSocket with that device_id.
    4. Connection stays open until the desktop disconnects.
    5. On disconnect, the device is removed from connected_devices.
    """
    await websocket.accept()
    device_id: str | None = None

    try:
        # First message from the desktop must be its device_id.
        device_id = await websocket.receive_text()

        if not devices.is_registered(device_id):
            await websocket.close(code=4404, reason="Device not registered")
            return

        devices.add_connection(device_id, websocket)

        # Keep the connection open, listening for further messages.
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass
    finally:
        if device_id is not None:
            devices.remove_connection(device_id)