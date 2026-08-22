import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import (
    CheckEmailRequest,
    ForgotPasswordRequest,
    RegisterRequest,
    RegisterResponse,
)
from app.schemas.device import LoginRequest, LoginResponse
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return RegisterResponse(
        success=True,
        message="Account created successfully.",
        id=user.id,
    )


@router.post("/login/initiate")
async def login_initiate(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        pending_token = await AuthService.initiate_login(db, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send login confirmation email.",
        )

    return {
        "success": True,
        "pending_token": pending_token,
        "message": "Verification email sent. Please check your inbox.",
    }


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await AuthService.login(db, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.get("/confirm-login")
async def confirm_login(
    token: str,
    action: str,
):
    try:
        message = await AuthService.confirm_login(token, action)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {"success": True, "message": message}


@router.get("/login/status")
async def check_login_status(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    session_data = AuthService._pending_logins_cache.get(token)

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification session does not exist or has expired.",
        )

    if time.time() > session_data["expires_at"]:
        AuthService._pending_logins_cache.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login request has expired.",
        )

    if session_data["status"] == "rejected":
        AuthService._pending_logins_cache.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Login request was rejected.",
        )

    if session_data["status"] == "approved":
        try:
            auth_response = await AuthService.login_after_approval(db, token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        return {"status": "approved", "data": auth_response}

    return {
        "status": "pending",
        "message": "Waiting for email confirmation...",
    }


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        await AuthService.request_password_reset(
            db,
            str(data.email),
            data.language,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to process password reset request.",
        )

    # Same response for existing/non-existing emails to avoid enumeration.
    return {
        "success": True,
        "message": "If the email exists, a password reset link has been sent.",
    }


@router.post("/check-email")
async def check_email(
    data: CheckEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    return await AuthService.check_email_exists(db, str(data.email))
