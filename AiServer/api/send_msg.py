import asyncio
import hashlib
import hmac
import os
import secrets
import time
from typing import Final

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from AiServer.rag.rag_runtime.core.config import settings

# ============================================================
# Configuration
# ============================================================

SERVER_TO_SERVER_SECRET: Final[str] = settings.SERVER_TO_SERVER_SECRET
REDIS_URL: Final[str] = os.environ.get(
    "REDIS_URL",
    "redis://127.0.0.1:6379/0",
)

MAX_CLOCK_SKEW_SECONDS: Final[int] = 300
MAX_MESSAGE_LENGTH: Final[int] = 20_000
MAX_BODY_BYTES: Final[int] = 64 * 1024

NONCE_TTL_SECONDS: Final[int] = MAX_CLOCK_SKEW_SECONDS + 30

RAG_SCRIPT: Final[str] = (
    "/home/badr-eldeen/Documents/ZenoServer/"
    "AiServer/rag/rag_tools/ask.py"
)

RAG_WORKING_DIRECTORY: Final[str] = (
    "/home/badr-eldeen/Documents/ZenoServer/AiServer/rag"
)

PYTHON_EXECUTABLE: Final[str] = os.environ.get(
    "RAG_PYTHON_EXECUTABLE",
    "/usr/bin/python3",
)


# ============================================================
# Redis
# ============================================================

redis = Redis.from_url(
    REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)


# ============================================================
# Router
# ============================================================

router = APIRouter(
    prefix="/send_message",
    tags=["internal-ai"],
)


# ============================================================
# Request model
# ============================================================

class MessageRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
    )


# ============================================================
# Security helpers
# ============================================================

def reject(message: str, code: int = status.HTTP_401_UNAUTHORIZED):
    raise HTTPException(
        status_code=code,
        detail=message,
    )


def get_secret_bytes() -> bytes:
    return SERVER_TO_SERVER_SECRET.encode("utf-8")


def build_signing_payload(
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes,
) -> bytes:
    """
    Everything important about the request is signed.

    Prevents an attacker from taking a valid signature and
    changing:
      - HTTP method
      - endpoint
      - body
      - timestamp
      - nonce
    """

    body_hash = hashlib.sha256(body).hexdigest()

    canonical = "\n".join(
        [
            method.upper(),
            path,
            timestamp,
            nonce,
            body_hash,
        ]
    )

    return canonical.encode("utf-8")


def calculate_signature(
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes,
) -> str:

    signing_payload = build_signing_payload(
        method=method,
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        body=body,
    )

    return hmac.new(
        get_secret_bytes(),
        signing_payload,
        hashlib.sha256,
    ).hexdigest()


async def verify_server_signature(
    request: Request,
) -> None:

    # --------------------------------------------------------
    # Required headers
    # --------------------------------------------------------

    signature = request.headers.get("X-Server-Signature")
    timestamp = request.headers.get("X-Request-Timestamp")
    nonce = request.headers.get("X-Request-Nonce")

    if not signature or not timestamp or not nonce:
        reject("Unauthorized")

    # --------------------------------------------------------
    # Basic header validation
    # --------------------------------------------------------

    if len(signature) != 64:
        reject("Unauthorized")

    if len(nonce) > 128:
        reject("Unauthorized")

    # --------------------------------------------------------
    # Timestamp validation
    # --------------------------------------------------------

    try:
        request_timestamp = int(timestamp)
    except ValueError:
        reject("Unauthorized")

    now = int(time.time())

    if abs(now - request_timestamp) > MAX_CLOCK_SKEW_SECONDS:
        reject("Request expired")

    # --------------------------------------------------------
    # Read raw body
    # --------------------------------------------------------

    body = await request.body()

    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Request body too large",
        )

    # --------------------------------------------------------
    # Verify HMAC
    # --------------------------------------------------------

    expected_signature = calculate_signature(
        method=request.method,
        path=request.url.path,
        timestamp=timestamp,
        nonce=nonce,
        body=body,
    )

    if not hmac.compare_digest(
        signature,
        expected_signature,
    ):
        reject("Unauthorized")

    # --------------------------------------------------------
    # Replay protection
    # --------------------------------------------------------

    nonce_key = f"zeno:ai:nonce:{nonce}"

    # SET NX EX is atomic.
    #
    # First request:
    #   result == True
    #
    # Replay:
    #   result == None
    #
    accepted = await redis.set(
        nonce_key,
        "1",
        ex=NONCE_TTL_SECONDS,
        nx=True,
    )

    if not accepted:
        reject("Replay detected")

    # --------------------------------------------------------
    # Optional request ID for logging / tracing
    # --------------------------------------------------------

    request.state.request_nonce = nonce


# ============================================================
# Endpoint
# ============================================================

@router.post(
    "",
    dependencies=[Depends(verify_server_signature)],
)
async def send_message(
    payload: MessageRequest,
    request: Request,
):
    """
    Internal-only AI gateway.

    This endpoint should never be exposed directly to users.
    """

    # --------------------------------------------------------
    # Generate internal correlation ID
    # --------------------------------------------------------

    request_id = getattr(
        request.state,
        "request_nonce",
        secrets.token_hex(16),
    )

    try:

        # ----------------------------------------------------
        # Execute RAG process
        # ----------------------------------------------------

        process = await asyncio.create_subprocess_exec(
            PYTHON_EXECUTABLE,
            RAG_SCRIPT,
            payload.message,

            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,

            cwd=RAG_WORKING_DIRECTORY,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120,
            )

        except asyncio.TimeoutError:

            process.kill()

            await process.wait()

            print(
                f"[AI][{request_id}] "
                "RAG process timed out"
            )

            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI request timed out",
            )

        # ----------------------------------------------------
        # Process failure
        # ----------------------------------------------------

        if process.returncode != 0:

            error_msg = stderr.decode(
                "utf-8",
                errors="replace",
            )

            # Do NOT return internal error details to caller.
            print(
                f"[AI][{request_id}] "
                f"RAG process failed: {error_msg}"
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate AI response",
            )

        # ----------------------------------------------------
        # Decode response
        # ----------------------------------------------------

        output = stdout.decode(
            "utf-8",
            errors="replace",
        ).strip()

        return {
            "response": output,
            "request_id": request_id,
        }

    except HTTPException:
        raise

    except Exception as exc:

        print(
            f"[AI][{request_id}] "
            f"Unexpected error: {exc}"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )