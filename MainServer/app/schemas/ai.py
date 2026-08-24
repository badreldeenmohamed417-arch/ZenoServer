from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AIRequestResponse(BaseModel):
    id: UUID
    status: str
    cost_tokens: int | None
    created_at: datetime
