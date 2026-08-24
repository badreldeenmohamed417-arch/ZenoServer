from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.current_user import get_current_user
from app.models.token_transaction import TokenTransaction
from app.models.user import User
from app.schemas.tokens import TokenBalanceResponse, TokenTransactionResponse
from app.services.token_service import TokenService

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get("/me", response_model=TokenBalanceResponse)
async def balance(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    wallet = await TokenService.get_wallet(db, user.id)
    return wallet


@router.get("/transactions", response_model=list[TokenTransactionResponse])
async def transactions(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return list(
        (
            await db.execute(
                select(TokenTransaction)
                .where(TokenTransaction.user_id == user.id)
                .order_by(TokenTransaction.created_at.desc())
            )
        ).scalars()
    )
