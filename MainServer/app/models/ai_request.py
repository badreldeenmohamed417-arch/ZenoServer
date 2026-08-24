import enum
from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import BaseModel


class AIRequestStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AIRequest(BaseModel):
    __tablename__ = "ai_requests"
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )

    message_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL")
    )

    provider: Mapped[str | None] = mapped_column(String(80))

    model: Mapped[str | None] = mapped_column(String(120))

    status: Mapped[AIRequestStatus] = mapped_column(
        Enum(AIRequestStatus, name="airequeststatus"), default=AIRequestStatus.PENDING
    )

    input_tokens: Mapped[int | None] = mapped_column(Integer)

    output_tokens: Mapped[int | None] = mapped_column(Integer)

    total_tokens: Mapped[int | None] = mapped_column(Integer)

    cost_tokens: Mapped[int | None] = mapped_column(Integer)

    latency_ms: Mapped[int | None] = mapped_column(Integer)

    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
