from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentResponse

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=list[PaymentResponse])
async def list_payments(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return list(
        (
            await db.execute(
                select(Payment)
                .where(Payment.user_id == user.id)
                .order_by(Payment.created_at.desc())
            )
        ).scalars()
    )
