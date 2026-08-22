from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    device_id: UUID
    teacher_name: str = Field(min_length=1, max_length=100)
    language: str = Field(default="ar", min_length=2, max_length=10)


class LoginResponse(BaseModel):
    access_token: str
    device_secret: str
    secret_expires_at: datetime
    is_primary: bool


class ChallengeRequest(BaseModel):
    device_id: UUID


class ChallengeResponse(BaseModel):
    nonce: str
    expires_at: datetime


class ChallengeVerify(BaseModel):
    device_id: UUID
    nonce: str
    response: str


class DeviceInfo(BaseModel):
    id: UUID
    teacher_name: str
    is_primary: bool
    is_active: bool
    last_seen: datetime
    created_at: datetime


class DeviceListResponse(BaseModel):
    count: int
    devices: list[DeviceInfo]


class SetPrimaryRequest(BaseModel):
    device_id: UUID
    password: str = Field(min_length=1, max_length=256)


class DeactivateDeviceRequest(BaseModel):
    device_id: UUID
    password: str = Field(min_length=1, max_length=256)
