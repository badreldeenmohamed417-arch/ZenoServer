"""
All SQLite-related code for the MasterKey server lives here.

Responsibility: persistent storage of registered devices.
Nothing in this file knows about FastAPI, WebSockets, or live connections.
"""

import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "devices.db"


def get_connection() -> sqlite3.Connection:
    """Open a new connection to the SQLite database.

    A fresh connection is created per call instead of keeping one global
    connection open, so the caller is responsible for closing it (or using
    a `with` block, since sqlite3.Connection supports the context manager
    protocol for commit/rollback -- we still close explicitly below).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    """Create the database file and the `devices` table if they don't exist."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_name TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def add_device(device_id: str, device_name: str) -> None:
    """Insert a device, or update its name if it already exists."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO devices (device_id, device_name)
            VALUES (?, ?)
            ON CONFLICT(device_id) DO UPDATE SET device_name = excluded.device_name
            """,
            (device_id, device_name),
        )
        conn.commit()
    finally:
        conn.close()


def get_device(device_id: str) -> Optional[sqlite3.Row]:
    """Return the row for a device, or None if it isn't registered."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT device_id, device_name FROM devices WHERE device_id = ?",
            (device_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def device_exists(device_id: str) -> bool:
    """Check whether a device is registered, without fetching its data."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT 1 FROM devices WHERE device_id = ?",
            (device_id,),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def remove_device(device_id: str) -> None:
    """Delete a device's registration record."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
        conn.commit()
    finally:
        conn.close()