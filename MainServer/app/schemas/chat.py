from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateConversationRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    subject_id: str | None = Field(default=None, max_length=100)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    lesson: str | None = Field(default=None, max_length=100)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    subject_id: str | None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    is_archived: bool


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
