from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.token_transaction import TokenTransactionType
from app.services.token_service import TokenService


class SubscriptionService:
    @staticmethod
    async def _free_plan(db: AsyncSession) -> Plan:
        plan = (
            await db.execute(select(Plan).where(Plan.name == "Free"))
        ).scalar_one_or_none()
        if not plan:
            plan = Plan(
                name="Free",
                description="Zeno starter plan",
                price=0,
                currency="USD",
                duration_days=30,
                token_limit=settings.DEFAULT_FREE_PLAN_TOKENS,
                is_active=True,
            )
            db.add(plan)
            await db.flush()
        return plan

    @staticmethod
    async def create_free_subscription(db: AsyncSession, user_id: UUID) -> Subscription:
        plan = await SubscriptionService._free_plan(db)
        now = datetime.now(timezone.utc)
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            status="active",
            started_at=now,
            expires_at=now + timedelta(days=plan.duration_days),
        )
        db.add(subscription)
        await db.flush()
        await TokenService.grant_tokens(
            db,
            user_id,
            plan.token_limit,
            TokenTransactionType.SUBSCRIPTION_GRANT,
            "Initial free subscription",
            str(subscription.id),
        )
        return subscription

    @staticmethod
    async def get_active_subscription(
        db: AsyncSession, user_id: UUID
    ) -> Subscription | None:
        now = datetime.now(timezone.utc)
        return (
            await db.execute(
                select(Subscription)
                .options(selectinload(Subscription.plan))
                .where(
                    Subscription.user_id == user_id,
                    Subscription.status == "active",
                    Subscription.expires_at > now,
                )
                .order_by(desc(Subscription.expires_at))
                .limit(1)
            )
        ).scalar_one_or_none()

    @staticmethod
    async def get_summary(
        db: AsyncSession, user_id: UUID
    ) -> tuple[Subscription | None, int]:
        subscription = await SubscriptionService.get_active_subscription(db, user_id)
        return subscription, await TokenService.get_balance(db, user_id)
