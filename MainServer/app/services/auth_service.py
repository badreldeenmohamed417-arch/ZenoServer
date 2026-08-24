import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.email_verification import EmailVerificationToken
from app.models.password_reset_token import PasswordResetToken
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import (
    CompleteDataRequest,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
)
from app.services.email_service import send_email_verification, send_password_reset
from app.services.subscription_service import SubscriptionService
from app.services.token_service import TokenService


class AuthService:
    @staticmethod
    async def send_verification_email(db: AsyncSession, user: User, language: str = "ar") -> None:
        if user.is_verified:
            return

        now = datetime.now(timezone.utc)

        # Rate Limiting: منع التكرار في وقت قصير (مثلاً دقيقتين)
        recent = (
            await db.execute(
                select(EmailVerificationToken)
                .where(
                    EmailVerificationToken.user_id == user.id,
                    EmailVerificationToken.created_at > now - timedelta(seconds=120)
                )
            )
        ).scalar_one_or_none()

        if recent:
            return

        token = secrets.token_urlsafe(32)
        db.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash=hash_token(token),
                created_at=now,
                expires_at=now + timedelta(hours=24),  # صلاحية 24 ساعة
            )
        )
        await db.commit()

        try:
            await send_email_verification(user.email, token, language)
        except Exception:
            return

    @staticmethod
    async def register(db: AsyncSession, data: RegisterRequest, language: str = "ar") -> User:
        email = str(data.email).strip().lower()

        # Check if user exists
        existing_user = (
            await db.execute(select(User.id).where(User.email == email))
        ).scalar_one_or_none()
        if existing_user:
            raise ValueError("Email already registered")

        user = User(
            email=email,
            password_hash=hash_password(data.password),
            auth_provider="email",
        )
        db.add(user)

        try:
            await db.flush()
            await TokenService.create_wallet(db, user.id)
            await SubscriptionService.create_free_subscription(db, user.id)
            await db.commit()
            await db.refresh(user)

            # إرسال إيميل التوثيق فور إتمام التسجيل
            await AuthService.send_verification_email(db, user, language=language)

            return user
        except IntegrityError:
            await db.rollback()
            raise ValueError("Email already registered")

    @staticmethod
    async def login(
        db: AsyncSession,
        data: LoginRequest,
        *,
        ip_address: str | None,
        user_agent: str | None,
        language: str = "ar",
    ) -> dict:
        email = str(data.email).strip().lower()
        user = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

        if (
            not user
            or not user.is_active
            or not user.password_hash
            or not verify_password(data.password, user.password_hash)
        ):
            raise ValueError("Invalid email or password")

        # إذا لم يكن الإيميل موثقاً، أرسل إيميل توثيق تلقائياً عند دخول المستخدم
        if not user.is_verified:
            await AuthService.send_verification_email(db, user, language=language)

        refresh_token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        session = Session(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            device_name=data.device_name,
            platform=data.platform,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            last_used_at=now,
        )
        db.add(session)
        await db.flush()
        await db.commit()

        return {
            "access_token": create_access_token(
                str(user.id), session_id=str(session.id)
            ),
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "session_id": session.id,
            "is_verified" : user.is_verified
        }

    @staticmethod
    async def complete_user_data(
        db: AsyncSession, user_id: str | int, data: CompleteDataRequest
    ) -> User:
        user = (
            await db.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        # Update profile attributes
        user.country = data.country
        if data.display_name is not None:
            user.display_name = data.display_name.strip()
        if data.grade is not None:
            user.grade = data.grade.strip()
        if data.school_system is not None:
            user.school_system = data.school_system.strip()
        user.language = data.language

        # Mark profile/data setup as completed if field exists
        if hasattr(user, "is_onboarded"):
            user.is_onboarded = True

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def refresh(db: AsyncSession, refresh_token: str) -> dict:
        now = datetime.now(timezone.utc)
        session = (
            await db.execute(
                select(Session)
                .where(Session.refresh_token_hash == hash_token(refresh_token))
                .with_for_update()
            )
        ).scalar_one_or_none()

        if not session or session.revoked_at or session.expires_at <= now:
            raise ValueError("Invalid or expired refresh token")

        new_token = secrets.token_urlsafe(48)
        session.refresh_token_hash = hash_token(new_token)  # Rotation prevents replay
        session.last_used_at = now
        await db.commit()

        return {
            "access_token": create_access_token(
                str(session.user_id), session_id=str(session.id)
            ),
            "refresh_token": new_token,
            "token_type": "bearer",
            "session_id": session.id,
        }

    @staticmethod
    async def logout(db: AsyncSession, session_id: str | int) -> None:
        await db.execute(
            update(Session)
            .where(Session.id == session_id, Session.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()

    @staticmethod
    async def logout_all(db: AsyncSession, user_id: str | int) -> None:
        await db.execute(
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()

    @staticmethod
    async def request_password_reset(
        db: AsyncSession, email: str, language: str = "ar"
    ) -> None:
        now = datetime.now(timezone.utc)
        user = (
            await db.execute(select(User).where(User.email == email.strip().lower()))
        ).scalar_one_or_none()

        if not user or not user.password_hash:
            return

        recent = (
            await db.execute(
                select(PasswordResetToken)
                .where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.created_at
                    > now
                    - timedelta(seconds=settings.PASSWORD_RESET_MIN_INTERVAL_SECONDS),
                )
                .limit(1)
            )
        ).scalar_one_or_none()

        if recent:
            return

        token = secrets.token_urlsafe(32)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(token),
                expires_at=now + timedelta(seconds=settings.PASSWORD_RESET_TTL_SECONDS),
            )
        )
        await db.commit()

        try:
            await send_password_reset(user.email, token, language)
        except Exception:
            return

    @staticmethod
    async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
        now = datetime.now(timezone.utc)
        reset = (
            await db.execute(
                select(PasswordResetToken)
                .where(PasswordResetToken.token_hash == hash_token(token))
                .with_for_update()
            )
        ).scalar_one_or_none()

        if not reset or reset.used_at or reset.expires_at <= now:
            raise ValueError("Reset token is invalid or expired")

        user = (
            await db.execute(select(User).where(User.id == reset.user_id))
        ).scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        user.password_hash = hash_password(new_password)
        reset.used_at = now

        await db.execute(
            update(Session)
            .where(Session.user_id == user.id, Session.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()

    @staticmethod
    async def google_login(
        db: AsyncSession,
        data: GoogleLoginRequest,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> dict:
        try:
            id_info = settings.google_id_token.verify_oauth2_token(
                data.id_token,
                settings.google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except Exception as exc:
            raise ValueError("Invalid Google ID token") from exc

        issuer = id_info.get("iss")
        if issuer not in {
            "accounts.google.com",
            "https://accounts.google.com",
        }:
            raise ValueError("Invalid Google token issuer")

        google_sub = id_info.get("sub")
        email = id_info.get("email")
        email_verified = id_info.get("email_verified", False)

        if not google_sub:
            raise ValueError("Google account ID is missing")
        if not email:
            raise ValueError("Google account email is missing")
        if not email_verified:
            raise ValueError("Google email is not verified")

        email = str(email).strip().lower()

        user = (
            await db.execute(
                select(User).where(
                    (User.google_sub == google_sub) | (User.email == email)
                )
            )
        ).scalar_one_or_none()

        is_new_user = False

        if not user:
            is_new_user = True
            user = User(
                email=email,
                password_hash=None,
                auth_provider="google",
                google_sub=google_sub,
                is_verified=True,
            )
            db.add(user)
            await db.flush()

            await TokenService.create_wallet(db, user.id)
            await SubscriptionService.create_free_subscription(db, user.id)
        else:
            if not user.google_sub:
                user.google_sub = google_sub
            if not user.is_verified:
                user.is_verified = True

        if not user.is_active:
            raise ValueError("User account is disabled")

        refresh_token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)

        session = Session(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            last_used_at=now,
        )

        db.add(session)
        await db.flush()
        await db.commit()

        return {
            "access_token": create_access_token(
                str(user.id),
                session_id=str(session.id),
            ),
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "session_id": session.id,
            "is_new_user": is_new_user,
        }

    @staticmethod
    async def verify_email(db: AsyncSession, token: str) -> None:
        now = datetime.now(timezone.utc)
        record = (
            await db.execute(
                select(EmailVerificationToken)
                .where(EmailVerificationToken.token_hash == hash_token(token))
                .with_for_update()
            )
        ).scalar_one_or_none()

        if not record or record.used_at or record.expires_at <= now:
            raise ValueError("Invalid or expired verification token")

        user = (
            await db.execute(select(User).where(User.id == record.user_id))
        ).scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        user.is_verified = True
        record.used_at = now
        await db.commit()