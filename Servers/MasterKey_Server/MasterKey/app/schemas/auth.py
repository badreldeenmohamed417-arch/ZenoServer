from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator

from app.core.security import validate_password_strength
from app.enums import MessagingService


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    country: str
    messaging_service: MessagingService = MessagingService.TELEGRAM

    @field_validator("password")
    @classmethod
    def validate_password_format(cls, value: str) -> str:
        is_valid, errors = validate_password_strength(value)
        if not is_valid:
            raise ValueError("Invalid password format: " + "; ".join(errors))
        return value

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise ValueError("country must be a 2-letter ISO country code")
        return value


class RegisterResponse(BaseModel):
    success: bool
    message: str
    id: UUID


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    language: str = "ar"


class CheckEmailRequest(BaseModel):
    email: EmailStr


class PasswordResetResponse(BaseModel):
    success: bool
    message: str
