from __future__ import annotations

from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_request import AIRequest, AIRequestStatus
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.user import User
from app.services.ai_service import AIService
from app.services.token_service import TokenService


class ChatService:
    """Coordinates persistence, AI completion, and token billing for chat."""

    def __init__(
        self,
        ai_service: AIService | None = None,
        token_service: type[TokenService] = TokenService,
    ) -> None:
        self.ai_service = ai_service or AIService()
        self.token_service = token_service

    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: UUID,
        title: str | None = None,
        subject_id: str | None = None,
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            title=title,
            subject_id=subject_id,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    async def list_conversations(
        self, db: AsyncSession, user_id: UUID
    ) -> list[Conversation]:
        result = await db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.is_archived.is_(False),
            )
            .order_by(Conversation.last_message_at.desc())
        )
        return list(result.scalars())

    async def get_conversation(
        self,
        db: AsyncSession,
        user_id: UUID,
        conversation_id: UUID,
        *,
        include_messages: bool = False,
    ) -> Conversation | None:
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.is_archived.is_(False),
        )
        if include_messages:
            statement = statement.options(selectinload(Conversation.messages))

        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def archive_conversation(
        self, db: AsyncSession, user_id: UUID, conversation_id: UUID
    ) -> bool:
        conversation = await self.get_conversation(db, user_id, conversation_id)
        if conversation is None:
            return False

        conversation.is_archived = True
        await db.commit()
        return True

    async def send_message(
        self,
        db: AsyncSession,
        user: User,
        conversation_id: UUID,
        content: str,
        lesson: str | None = None,
    ) -> tuple[Message, Message, AIRequest]:
        """Store a user message, bill it, and persist the generated response.

        The initial commit intentionally happens before contacting the remote AI
        server. It releases the wallet row lock held while reserving tokens and
        leaves an auditable running request if that server becomes unavailable.
        """
        conversation = await self.get_conversation(db, user.id, conversation_id)
        if conversation is None:
            raise ValueError("Conversation not found")

        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=content,
        )
        db.add(user_message)
        await db.flush()

        ai_request = AIRequest(
            user_id=user.id,
            conversation_id=conversation.id,
            message_id=user_message.id,
            status=AIRequestStatus.RUNNING,
        )
        db.add(ai_request)
        await db.flush()

        transaction = await self.token_service.spend_tokens_for_message(
            db=db,
            user_id=user.id,
            message_text=content,
            reason="Chat message usage",
            reference_id=str(ai_request.id),
            extra_metadata={"conversation_id": str(conversation.id)},
        )
        ai_request.cost_tokens = -transaction.amount
        conversation.last_message_at = user_message.created_at
        await db.commit()

        try:
            messages = await self._conversation_messages(db, conversation.id)
            context = [{"lesson": lesson}] if lesson else []
            started_at = perf_counter()
            completion = await self.ai_service.complete(
                messages=messages,
                context=context,
            )
            latency_ms = round((perf_counter() - started_at) * 1000)
        except Exception as exc:
            await self._record_failed_request(db, user.id, ai_request, exc)
            raise

        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=completion.content,
        )
        db.add(assistant_message)
        ai_request.provider = completion.provider
        ai_request.model = completion.model
        ai_request.input_tokens = completion.input_tokens
        ai_request.output_tokens = completion.output_tokens
        ai_request.total_tokens = self._total_tokens(
            completion.input_tokens, completion.output_tokens
        )
        ai_request.latency_ms = latency_ms
        ai_request.status = AIRequestStatus.COMPLETED
        conversation.last_message_at = assistant_message.created_at
        await db.commit()
        await db.refresh(assistant_message)
        return user_message, assistant_message, ai_request

    async def _conversation_messages(
        self, db: AsyncSession, conversation_id: UUID
    ) -> list[dict[str, str]]:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return [
            {"role": message.role.value, "content": message.content}
            for message in result.scalars()
        ]

    async def _record_failed_request(
        self,
        db: AsyncSession,
        user_id: UUID,
        ai_request: AIRequest,
        error: Exception,
    ) -> None:
        ai_request.status = AIRequestStatus.FAILED
        ai_request.error_message = str(error)[:10_000]

        if ai_request.cost_tokens:
            await self.token_service.refund_tokens(
                db=db,
                user_id=user_id,
                amount=ai_request.cost_tokens,
                reason="Chat message refund after AI failure",
                reference_id=str(ai_request.id),
            )
        await db.commit()

    @staticmethod
    def _total_tokens(input_tokens: int | None, output_tokens: int | None) -> int | None:
        if input_tokens is None and output_tokens is None:
            return None
        return (input_tokens or 0) + (output_tokens or 0)
