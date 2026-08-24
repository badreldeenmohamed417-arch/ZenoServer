from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    # Auth details
    auth_provider: Mapped[str] = mapped_column(
        String(20), nullable=False, default="email"
    )  # 'email' or 'google'
    google_sub: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    # Profile details (optional until complete_user_data is called)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    school_system: Mapped[str | None] = mapped_column(String(80), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="ar")

    # Flags
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_onboarded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    wallet = relationship(
        "TokenWallet",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )