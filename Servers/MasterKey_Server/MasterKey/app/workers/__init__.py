# Import the queue first so Dramatiq uses the configured Redis broker.
from app.core import queue as _queue  # noqa: F401

from .message_worker import send_messages

__all__ = ["send_messages"]
