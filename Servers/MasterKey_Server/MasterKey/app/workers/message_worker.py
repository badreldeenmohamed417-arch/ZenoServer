import logging

import dramatiq
import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

TELEGRAM_SERVICE_URL = "http://127.0.0.1:8000/send"
SYNC_DATABASE_URL = settings.DATABASE_URL.replace("+asyncpg", "")
sync_engine = create_engine(SYNC_DATABASE_URL, pool_pre_ping=True)


@dramatiq.actor(max_retries=3, min_backoff=5000)
def send_messages(
    numbers: list[str],
    text: str,
    sending_way: str,
    user_id: str,
):
    if sending_way.lower() != "telegram":
        raise ValueError(f"Unsupported messaging service: {sending_way}")

    payload = {
        "phone_numbers": numbers,
        "text": text,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(TELEGRAM_SERVICE_URL, json=payload)
        response.raise_for_status()
        result = response.json()

    delivered = int(result.get("delivered", 0))
    failed = int(result.get("failed", 0))
    not_registered = int(result.get("not_registered", 0))

    # Current project pricing is 1 balance unit per delivered message.
    total_cost = delivered

    # Keep the usage counter and balance update in the main database.
    with Session(sync_engine) as db:
        user = db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()

        if user is None:
            raise RuntimeError(f"User {user_id} not found")

        refunded = max(0, len(numbers) - delivered)
        user.messages_used += delivered
        user.balance += refunded
        db.commit()

    logger.info(
        "Telegram dispatch user=%s delivered=%s failed=%s not_registered=%s",
        user_id,
        delivered,
        failed,
        not_registered,
    )

    return {
        "status": "completed",
        "user_id": user_id,
        "delivered": delivered,
        "failed": failed,
        "not_registered": not_registered,
    }
