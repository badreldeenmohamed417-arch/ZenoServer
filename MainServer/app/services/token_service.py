import math
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token_transaction import TokenTransaction, TokenTransactionType
from app.models.token_wallet import TokenWallet


class InsufficientTokensError(ValueError):
    pass


class TokenService:
    # -------------------------------------------------------------
    # حساب التكلفة بناءً على عدد الحروف (Characters)
    # -------------------------------------------------------------
    @staticmethod
    def calculate_message_cost(
            text: str,
            rate_per_char: float = 0.25,  # معدل التوكنز لكل حرف (مثلاً: 0.25 تعني كل 4 حروف = 1 توكن)
            min_cost: int = 1,  # الحد الأدنى للخصم لكل رسالة
    ) -> int:
        """
        تحسب عدد الـ Tokens بناءً على عدد الحروف في الرسالة.
        """
        if not text or not text.strip():
            return 0

        char_count = len(text)
        calculated_cost = math.ceil(char_count * rate_per_char)

        return max(calculated_cost, min_cost)

    @staticmethod
    async def create_wallet(db: AsyncSession, user_id: UUID) -> TokenWallet:
        wallet = TokenWallet(user_id=user_id)
        db.add(wallet)
        await db.flush()
        return wallet

    @staticmethod
    async def get_wallet(db: AsyncSession, user_id: UUID) -> TokenWallet:
        result = await db.execute(
            select(TokenWallet).where(TokenWallet.user_id == user_id)
        )
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise ValueError("Wallet not found")
        return wallet

    @staticmethod
    async def get_balance(db: AsyncSession, user_id: UUID) -> int:
        return (await TokenService.get_wallet(db, user_id)).balance

    @staticmethod
    async def record_transaction(
            db: AsyncSession,
            wallet: TokenWallet,
            transaction_type: TokenTransactionType,
            amount: int,
            reason: str,
            reference_id: str | None = None,
            metadata: dict | None = None,
    ) -> TokenTransaction:
        transaction = TokenTransaction(
            user_id=wallet.user_id,
            wallet_id=wallet.id,
            type=transaction_type,
            amount=amount,
            balance_after=wallet.balance,
            reason=reason,
            reference_id=reference_id,
            metadata_=metadata,
        )
        db.add(transaction)
        await db.flush()
        return transaction

    @staticmethod
    async def _locked_wallet(db: AsyncSession, user_id: UUID) -> TokenWallet:
        result = await db.execute(
            select(TokenWallet).where(TokenWallet.user_id == user_id).with_for_update()
        )
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise ValueError("Wallet not found")
        return wallet

    @staticmethod
    async def grant_tokens(
            db: AsyncSession,
            user_id: UUID,
            amount: int,
            transaction_type: TokenTransactionType,
            reason: str,
            reference_id: str | None = None,
            metadata: dict | None = None,
    ) -> TokenTransaction:
        if amount <= 0:
            raise ValueError("Token amount must be positive")

        async with db.begin_nested():
            wallet = await TokenService._locked_wallet(db, user_id)
            wallet.balance += amount
            wallet.total_earned += amount
            transaction = await TokenService.record_transaction(
                db, wallet, transaction_type, amount, reason, reference_id, metadata
            )
        return transaction

    @staticmethod
    async def spend_tokens(
            db: AsyncSession,
            user_id: UUID,
            amount: int,
            reason: str,
            reference_id: str | None = None,
            metadata: dict | None = None,
    ) -> TokenTransaction:
        if amount <= 0:
            raise ValueError("Token amount must be positive")

        async with db.begin_nested():
            wallet = await TokenService._locked_wallet(db, user_id)
            if wallet.balance < amount:
                raise InsufficientTokensError("Insufficient token balance")

            wallet.balance -= amount
            wallet.total_spent += amount
            transaction = await TokenService.record_transaction(
                db,
                wallet,
                TokenTransactionType.AI_USAGE,
                -amount,
                reason,
                reference_id,
                metadata,
            )
        return transaction

    # -------------------------------------------------------------
    # الخصم المباشر بناءً على عدد الحروف
    # -------------------------------------------------------------
    @staticmethod
    async def spend_tokens_for_message(
            db: AsyncSession,
            user_id: UUID,
            message_text: str,
            rate_per_char: float = 0.25,
            reason: str = "AI Message Usage",
            reference_id: str | None = None,
            extra_metadata: dict | None = None,
    ) -> TokenTransaction:
        char_count = len(message_text) if message_text else 0
        cost = TokenService.calculate_message_cost(message_text, rate_per_char=rate_per_char)

        metadata = {
            "char_count": char_count,
            "rate_per_char": rate_per_char,
            "calculated_cost": cost,
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        return await TokenService.spend_tokens(
            db=db,
            user_id=user_id,
            amount=cost,
            reason=reason,
            reference_id=reference_id,
            metadata=metadata,
        )

    @staticmethod
    async def refund_tokens(
            db: AsyncSession,
            user_id: UUID,
            amount: int,
            reason: str,
            reference_id: str | None = None,
    ) -> TokenTransaction:
        return await TokenService.grant_tokens(
            db,
            user_id,
            amount,
            TokenTransactionType.REFUND,
            reason,
            reference_id,
        )