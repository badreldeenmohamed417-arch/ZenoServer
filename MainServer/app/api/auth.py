from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.dependencies.current_user import get_current_user
from app.models.user import User
from app.schemas.auth import (
    CompleteDataRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await AuthService.register(db, data)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    return RegisterResponse(
        success=True,
        message="Account created successfully.",
        id=user.id,
    )


@router.post("/complete-data", response_model=UserResponse)
async def complete_data(
    data: CompleteDataRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        updated_user = await AuthService.complete_user_data(
            db=db,
            user_id=current_user.id,
            data=data,
        )
        return updated_user
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await AuthService.login(
            db,
            data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await AuthService.refresh(db, data.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    auth_header = request.headers.get("authorization", "")
    if " " not in auth_header:
        return

    payload = decode_access_token(auth_header.split(" ", 1)[1])
    if payload and "session_id" in payload:
        await AuthService.logout(db, payload["session_id"])


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await AuthService.logout_all(db, user.id)


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await AuthService.request_password_reset(db, str(data.email), data.language)
    return {
        "success": True,
        "message": "If the email exists, a password reset link has been sent.",
    }


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        await AuthService.reset_password(db, data.token, data.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/google", response_model=TokenResponse)
async def google_login(
    data: GoogleLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await AuthService.google_login(
            db,
            data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        ) from exc

from app.schemas.auth import VerifyEmailRequest, ResendVerificationRequest

@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        await AuthService.verify_email(db, data.token)
        return {"success": True, "message": "Email verified successfully."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    data: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    user = (
        await db.execute(select(User).where(User.email == data.email.strip().lower()))
    ).scalar_one_or_none()

    if user and not user.is_verified:
        await AuthService.send_verification_email(db, user, data.language)

    # حماية من Enumeration attack: نرجع نفس الرد دائماً
    return {
        "success": True,
        "message": "If the account exists and is not verified, a verification link has been sent.",
    }