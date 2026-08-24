from datetime import datetime

from pydantic import BaseModel


class SubscriptionResponse(BaseModel):
    current_plan: str | None
    status: str | None
    started_at: datetime | None
    expires_at: datetime | None
    available_token_balance: int
    entitlements: dict[str, int | bool]
