from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.message import SendMessageRequest, SendMessageResponse
from app.workers import send_messages

router = APIRouter(prefix="/messages", tags=["messages"])


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .options(joinedload(User.subscription))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    subscription: Subscription | None = user.subscription
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No subscription found for this user.",
        )

    if str(subscription.status).lower() != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Subscription is inactive (Status: {subscription.status}).",
        )

    now = datetime.now(timezone.utc)
    if _ensure_utc(subscription.end_date) <= now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription has expired. Please renew to continue sending messages.",
        )

    # The existing worker charges one unit per delivered message.
    # Reserve the requested amount before enqueueing so users cannot send with
    # zero balance. If the queue call fails, roll the reservation back.
    requested_cost = len(data.recipients)
    if user.balance < requested_cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient balance.",
        )

    user.balance -= requested_cost

    try:
        await db.commit()
        send_messages.send(
            numbers=data.recipients,
            text=data.text,
            sending_way=data.sending_way.value,
            user_id=str(user.id),
        )
    except Exception:
        user.balance += requested_cost
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to queue the messages.",
        )

    return SendMessageResponse(
        success=True,
        message="Message queued successfully.",
    )
