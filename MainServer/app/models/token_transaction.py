import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import BaseModel


class TokenTransactionType(str, enum.Enum):
    SUBSCRIPTION_GRANT = "subscription_grant"
    PURCHASE = "purchase"
    AI_USAGE = "ai_usage"
    REFUND = "refund"
    BONUS = "bonus"
    ADMIN_ADJUSTMENT = "admin_adjustment"


class TokenTransaction(BaseModel):
    __tablename__ = "token_transactions"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    wallet_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "token_wallets.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    type: Mapped[TokenTransactionType] = mapped_column(
        Enum(TokenTransactionType, name="tokentransactiontype")
    )

    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)

    reason: Mapped[str] = mapped_column(String(255), nullable=False)

    reference_id: Mapped[str | None] = mapped_column(String(128))

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    wallet = relationship("TokenWallet", back_populates="transactions")
