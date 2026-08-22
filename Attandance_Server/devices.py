"""
Application logic for devices.

Two separate concepts live here, and they must not be confused:

1. Registered devices  -> permanent, stored in SQLite (via database.py)
2. Connected devices    -> temporary, live WebSocket connections held in memory

The rest of the server should go through the functions below instead of
touching `database.py` or the `connected_devices` dict directly.
"""

from typing import Optional

from fastapi import WebSocket

import database

# In-memory registry of currently-connected WebSocket clients.
# Maps device_id -> WebSocket. This is NOT persisted anywhere.
connected_devices: dict[str, WebSocket] = {}


# ---------------------------------------------------------------------------
# Registered devices (backed by SQLite)
# ---------------------------------------------------------------------------

def register_device(device_id: str, device_name: str) -> None:
    """Register a device permanently. Safe to call again for the same device."""
    database.add_device(device_id, device_name)


def get_registered_device(device_id: str):
    """Return the registered device row, or None if it has never registered."""
    return database.get_device(device_id)


def is_registered(device_id: str) -> bool:
    """Whether a device has a permanent registration record."""
    return database.device_exists(device_id)


# ---------------------------------------------------------------------------
# Connected devices (in-memory only, live for the life of the WebSocket)
# ---------------------------------------------------------------------------

def add_connection(device_id: str, websocket: WebSocket) -> None:
    """Mark a device as currently connected via WebSocket."""
    connected_devices[device_id] = websocket


def remove_connection(device_id: str) -> None:
    """Remove a device from the live-connections map, if present."""
    connected_devices.pop(device_id, None)


def get_connection(device_id: str) -> Optional[WebSocket]:
    """Return the live WebSocket for a device, or None if it's not connected."""
    return connected_devices.get(device_id)


def is_connected(device_id: str) -> bool:
    """Whether a device currently has a live WebSocket connection."""
    return device_id in connected_devices