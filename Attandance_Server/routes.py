"""
HTTP API routes for the MasterKey server.

Only three concerns live here: request/response shapes and calling into
devices.py. No SQLite and no WebSocket-handling logic in this file.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import devices

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    device_id: str
    device_name: str


class LoginRequest(BaseModel):
    device_id: str


class AttendanceRequest(BaseModel):
    device_id: str
    payload: dict | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/")
def health_check():
    return {"status": "ok"}


@router.post("/register")
def register(request: RegisterRequest):
    """Register (or re-register) a MasterKey Desktop computer."""
    devices.register_device(request.device_id, request.device_name)
    return {"success": True, "device_id": request.device_id}


@router.post("/login")
def login(request: LoginRequest):
    """Used by MasterKey Mobile to look up a registered computer.

    NOTE: being registered in SQLite does NOT mean the device is currently
    online. That is tracked separately via the /ws WebSocket connections.
    """
    device = devices.get_registered_device(request.device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not registered")

    return {
        "device_id": device["device_id"],
        "device_name": device["device_name"],
        "is_online": devices.is_connected(device["device_id"]),
    }


@router.post("/attendance")
def attendance(request: AttendanceRequest):
    """Placeholder endpoint. Full attendance logic is not implemented yet."""
    if not devices.is_registered(request.device_id):
        raise HTTPException(status_code=404, detail="Device not registered")

    # TODO: forward/store encrypted attendance data once that system exists.
    return {"success": True, "received": True}