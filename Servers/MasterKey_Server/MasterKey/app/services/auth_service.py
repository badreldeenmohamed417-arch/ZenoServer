import logging
import secrets
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import encrypt_secret
from app.core.security import create_access_token, hash_password, verify_password
from app.models.device import Device
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.device import LoginRequest, LoginResponse
from app.services.email_service import (
    send_login_alert_via_brevo,
    send_reset_code_via_brevo,
)

logger = logging.getLogger(__name__)


class AuthService:
    _reset_tokens_cache: dict[str, dict] = {}
    _reset_last_sent: dict[str, float] = {}
    _login_last_sent: dict[str, float] = {}
    _pending_logins_cache: dict[str, dict] = {}

    @staticmethod
    async def register(db: AsyncSession, data: RegisterRequest) -> User:
        email = str(data.email).strip().lower()

        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        user = User(
            email=email,
            password_hash=hash_password(data.password),
            country=data.country,
            messaging_service=data.messaging_service,
            messages_used=0,
            balance=0,
        )
        db.add(user)
        await db.flush()

        now = datetime.now(timezone.utc)
        db.add(
            Subscription(
                user_id=user.id,
                plan="free",
                status="active",
                start_date=now,
                end_date=now + timedelta(days=30),
            )
        )

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def _issue_device_credentials(
        db: AsyncSession,
        user: User,
        data: LoginRequest,
    ) -> LoginResponse:
        result = await db.execute(
            select(Device).where(
                Device.id == data.device_id,
                Device.user_id == user.id,
            )
        )
        device = result.scalar_one_or_none()

        plain_secret = secrets.token_hex(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.DEVICE_SECRET_TTL_DAYS)

        if device:
            device.teacher_name = data.teacher_name
            device.device_secret_encrypted = encrypt_secret(plain_secret)
            device.secret_expires_at = expires_at
            device.is_active = True
            device.last_seen = now
        else:
            result = await db.execute(
                select(Device.id).where(Device.user_id == user.id).limit(1)
            )
            has_any_device = result.first() is not None

            device = Device(
                id=data.device_id,
                user_id=user.id,
                teacher_name=data.teacher_name,
                device_secret_encrypted=encrypt_secret(plain_secret),
                secret_expires_at=expires_at,
                is_primary=not has_any_device,
                is_active=True,
                last_seen=now,
            )
            db.add(device)

        await db.commit()
        await db.refresh(device)

        return LoginResponse(
            access_token=create_access_token(
                subject=str(user.id),
                device_id=str(device.id),
            ),
            device_secret=plain_secret,
            secret_expires_at=expires_at,
            is_primary=device.is_primary,
        )

    @staticmethod
    async def login(db: AsyncSession, data: LoginRequest) -> LoginResponse:
        email = str(data.email).strip().lower()
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            raise ValueError("Invalid email or password")

        response = await AuthService._issue_device_credentials(db, user, data)

        # Security alert is useful, but it must not make a successful login fail
        # after the database transaction has already committed.
        try:
            login_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            await send_login_alert_via_brevo(
                to_email=user.email,
                device_name=data.teacher_name or "Unknown Device",
                login_time=login_time,
                language=data.language,
            )
        except Exception:
            logger.exception("Failed to send login alert for user %s", user.id)

        return response

    @staticmethod
    async def request_password_reset(
        db: AsyncSession,
        email: str,
        language: str = "ar",
    ) -> None:
        email = email.strip().lower()
        now = time.time()

        last_sent = AuthService._reset_last_sent.get(email, 0)
        if now - last_sent < settings.PASSWORD_RESET_MIN_INTERVAL_SECONDS:
            return

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        # Deliberately return the same external behavior whether the email exists
        # or not, preventing account enumeration.
        if not user:
            return

        token = secrets.token_urlsafe(32)
        expires_at = now + settings.PASSWORD_RESET_TTL_SECONDS

        AuthService._reset_tokens_cache[token] = {
            "email": email,
            "expires_at": expires_at,
        }
        AuthService._reset_last_sent[email] = now

        try:
            await send_reset_code_via_brevo(
                to_email=user.email,
                token=token,
                language=language,
            )
        except Exception:
            AuthService._reset_tokens_cache.pop(token, None)
            raise

    @staticmethod
    async def check_email_exists(db: AsyncSession, email: str):
        result = await db.execute(
            select(User).where(User.email == email.strip().lower())
        )
        return {"exists": result.scalar_one_or_none() is not None}

    @staticmethod
    async def initiate_login(db: AsyncSession, data: LoginRequest) -> str:
        email = str(data.email).strip().lower()
        now = time.time()

        last_sent = AuthService._login_last_sent.get(email, 0)
        if now - last_sent < settings.LOGIN_INITIATE_MIN_INTERVAL_SECONDS:
            raise ValueError("Please wait before requesting another login confirmation")

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            raise ValueError("Invalid email or password")

        pending_token = secrets.token_urlsafe(32)
        expires_at = now + settings.LOGIN_APPROVAL_TTL_SECONDS

        # Never store the user's plaintext password in the temporary cache.
        AuthService._pending_logins_cache[pending_token] = {
            "user_id": user.id,
            "device_id": data.device_id,
            "teacher_name": data.teacher_name,
            "language": data.language,
            "expires_at": expires_at,
            "status": "pending",
        }
        AuthService._login_last_sent[email] = now

        login_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        try:
            await send_login_alert_via_brevo(
                to_email=user.email,
                device_name=data.teacher_name or "Unknown Device",
                login_time=login_time,
                language=data.language,
                pending_token=pending_token,
            )
        except Exception:
            AuthService._pending_logins_cache.pop(pending_token, None)
            raise

        return pending_token

    @staticmethod
    async def confirm_login(token: str, action: str) -> str:
        pending = AuthService._pending_logins_cache.get(token)
        if not pending:
            raise ValueError("Confirmation link is invalid or has expired.")

        if time.time() > pending["expires_at"]:
            AuthService._pending_logins_cache.pop(token, None)
            raise ValueError("Confirmation link has expired.")

        if pending["status"] != "pending":
            raise ValueError("This login request has already been processed.")

        if action == "yes":
            pending["status"] = "approved"
            return "Login successfully confirmed. You can now return to the application."

        if action == "no":
            pending["status"] = "rejected"
            return "Login attempt successfully rejected and session blocked."

        raise ValueError("Invalid action.")

    @staticmethod
    async def login_after_approval(
        db: AsyncSession,
        token: str,
    ) -> LoginResponse:
        pending = AuthService._pending_logins_cache.get(token)
        if not pending:
            raise ValueError("Verification session does not exist or has expired.")

        if time.time() > pending["expires_at"]:
            AuthService._pending_logins_cache.pop(token, None)
            raise ValueError("Login request has expired.")

        if pending["status"] == "rejected":
            AuthService._pending_logins_cache.pop(token, None)
            raise ValueError("Login attempt was rejected by the user.")

        if pending["status"] != "approved":
            raise ValueError("Login has not been confirmed from the email yet.")

        result = await db.execute(
            select(User).where(User.id == pending["user_id"])
        )
        user = result.scalar_one_or_none()
        if not user:
            AuthService._pending_logins_cache.pop(token, None)
            raise ValueError("User not found.")

        data = LoginRequest(
            email=user.email,
            password="approved-login",
            device_id=pending["device_id"],
            teacher_name=pending["teacher_name"],
            language=pending["language"],
        )

        response = await AuthService._issue_device_credentials(db, user, data)
        AuthService._pending_logins_cache.pop(token, None)
        return response

    @staticmethod
    async def reset_password(
        db: AsyncSession,
        token: str,
        new_password: str,
    ) -> None:
        pending = AuthService._reset_tokens_cache.get(token)
        if not pending:
            raise ValueError("Reset link is invalid or has expired.")

        if time.time() > pending["expires_at"]:
            AuthService._reset_tokens_cache.pop(token, None)
            raise ValueError("Reset link has expired.")

        result = await db.execute(
            select(User).where(User.email == pending["email"])
        )
        user = result.scalar_one_or_none()
        if not user:
            AuthService._reset_tokens_cache.pop(token, None)
            raise ValueError("User not found.")

        user.password_hash = hash_password(new_password)
        await db.commit()
        AuthService._reset_tokens_cache.pop(token, None)
