from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    country: str
    display_name: str | None
    grade: str | None
    school_system: str | None
    language: str
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UpdateUserRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    grade: str | None = Field(default=None, max_length=50)
    school_system: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, max_length=10)
    country: str | None = Field(default=None, min_length=2, max_length=2)
