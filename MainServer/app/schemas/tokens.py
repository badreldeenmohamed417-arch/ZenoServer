from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TokenBalanceResponse(BaseModel):
    balance: int
    total_earned: int
    total_spent: int


class TokenTransactionResponse(BaseModel):
    id: UUID
    type: str
    amount: int
    balance_after: int
    reason: str
    reference_id: str | None
    created_at: datetime
