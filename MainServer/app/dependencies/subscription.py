from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.subscription import Subscription
from app.models.user import User
from app.services.subscription_service import SubscriptionService


async def require_active_subscription(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Subscription:
    subscription = await SubscriptionService.get_active_subscription(db, user.id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active subscription is required",
        )
    return subscription
