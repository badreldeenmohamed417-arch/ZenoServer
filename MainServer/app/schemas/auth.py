from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from app.core.security import validate_password_strength


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        valid, errors = validate_password_strength(value)
        if not valid:
            raise ValueError("Invalid password format: " + "; ".join(errors))
        return value


class RegisterResponse(BaseModel):
    success: bool
    message: str
    id: UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_name: str | None = Field(default=None, max_length=120)
    platform: str | None = Field(default=None, max_length=80)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    session_id: UUID | int
    is_new_user: bool = False
    is_verified: bool = True

class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=32, max_length=1024)

class ResendVerificationRequest(BaseModel):
    email: EmailStr
    language: str = "ar"

class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=1024)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    language: str = "ar"


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=1024)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        valid, errors = validate_password_strength(value)
        if not valid:
            raise ValueError("Invalid password format: " + "; ".join(errors))
        return value

class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=100)

class CompleteDataRequest(BaseModel):
    country: str
    display_name: str | None = Field(default=None, max_length=120)
    grade: str | None = Field(default=None, max_length=50)
    school_system: str | None = Field(default=None, max_length=80)
    language: str = Field(default="ar", max_length=10)

    @field_validator("country")
    @classmethod
    def country_code(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise ValueError("country must be a 2-letter ISO country code")
        return value

class UserResponse(BaseModel):
    id: UUID | int = Field(..., description="Unique user identifier")
    email: EmailStr
    is_active: bool
    is_onboarded: bool = False
    country: str | None = None
    display_name: str | None = None
    grade: str | None = None
    school_system: str | None = None
    language: str = "ar"

    model_config = ConfigDict(from_attributes=True)


