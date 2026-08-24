from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PaymentResponse(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    provider: str
    status: str
    created_at: datetime
