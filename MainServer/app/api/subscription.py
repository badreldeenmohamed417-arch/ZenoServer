from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.user import User
from app.schemas.subscription import SubscriptionResponse
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/me", response_model=SubscriptionResponse)
async def my_subscription(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    subscription, balance = await SubscriptionService.get_summary(db, user.id)
    plan = subscription.plan if subscription else None
    return SubscriptionResponse(
        current_plan=plan.name if plan else None,
        status=subscription.status if subscription else None,
        started_at=subscription.started_at if subscription else None,
        expires_at=subscription.expires_at if subscription else None,
        available_token_balance=balance,
        entitlements={
            "chat": bool(subscription),
            "token_limit": plan.token_limit if plan else 0,
        },
    )
