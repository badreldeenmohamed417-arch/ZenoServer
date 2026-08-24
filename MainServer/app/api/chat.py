from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.current_user import get_current_user
from app.dependencies.subscription import require_active_subscription
from app.models.user import User
from app.schemas.chat import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    SendMessageRequest,
)
from app.services.ai_service import AIProviderUnavailable
from app.services.chat_service import ChatService
from app.services.token_service import InsufficientTokensError

router = APIRouter(prefix="/chat", tags=["chat"])
service = ChatService()


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    data: CreateConversationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_conversation(db, user.id, data.title, data.subject_id)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return {"items": await service.list_conversations(db, user.id)}


@router.get(
    "/conversations/{conversation_id}", response_model=ConversationDetailResponse
)
async def get_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        conversation = await service.get_conversation(
            db, user.id, conversation_id, include_messages=True
        )
        if not conversation:
            raise HTTPException(404, "Conversation not found")
    except Exception as exc:
        raise HTTPException(500, detail="حدث خطأ غير متوقع أثناء معالجة الطلب") from exc
    return conversation


@router.post(
    "/conversations/{conversation_id}/messages", response_model=MessageResponse
)
async def send_message(
    conversation_id: UUID,
    data: SendMessageRequest,
    user: User = Depends(get_current_user),
    _subscription=Depends(require_active_subscription),
    db: AsyncSession = Depends(get_db),
):
    try:
        _, assistant_message, _ = await service.send_message(
            db, user, conversation_id, data.content, data.lesson
        )
    except InsufficientTokensError as exc:
        raise HTTPException(402, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except AIProviderUnavailable as exc:
        raise HTTPException(
            503, "AI is not configured yet; reserved tokens were refunded"
        ) from exc
    return assistant_message


@router.delete(
    "/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def archive_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await service.archive_conversation(db, user.id, conversation_id):
        raise HTTPException(404, "Conversation not found")
