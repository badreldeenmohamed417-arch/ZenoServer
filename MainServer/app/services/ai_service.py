from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


# ============================================================
# Exceptions
# ============================================================

class AIProviderUnavailable(RuntimeError):
    pass


class AIProviderRequestError(RuntimeError):
    pass


# ============================================================
# Completion
# ============================================================

@dataclass
class AICompletion:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    provider: str | None = None
    model: str | None = None


# ============================================================
# Provider interface
# ============================================================

class AIProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        context: list[dict[str, Any]],
    ) -> AICompletion:
        ...


# ============================================================
# Configuration
# ============================================================

AI_SERVER_URL = os.getenv(
    "AI_SERVER_URL",
    "https://127.0.0.1:8443",
).rstrip("/")

AI_SERVER_SECRET = settings.SERVER_TO_SERVER_SECRET

AI_SERVER_TIMEOUT = float(
    os.getenv("AI_SERVER_TIMEOUT", "130")
)

AI_SERVER_PATH = "/send_message"


# ============================================================
# Remote AI Provider
# ============================================================

class RemoteAIProvider(AIProvider):
    """
    Main Server -> AI Server provider.

    Security:
        HTTPS
        +
        HMAC-SHA256
        +
        timestamp
        +
        nonce
        +
        body hash
    """

    def __init__(
        self,
        *,
        base_url: str = AI_SERVER_URL,
        secret: str = AI_SERVER_SECRET,
        timeout: float = AI_SERVER_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.timeout = timeout

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                read=timeout,
                write=10.0,
                pool=10.0,
            ),
        )

    # --------------------------------------------------------
    # Signature
    # --------------------------------------------------------

    def _sign_request(
        self,
        *,
        method: str,
        path: str,
        body: bytes,
        timestamp: str,
        nonce: str,
    ) -> str:

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

        return hmac.new(
            self.secret.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        context: list[dict[str, Any]],
    ) -> AICompletion:

        # ----------------------------------------------------
        # Build the user message
        # ----------------------------------------------------

        user_message = ""

        for message in reversed(messages):
            if message.get("role") == "user":
                user_message = message.get("content", "")
                break

        if not user_message:
            raise AIProviderRequestError(
                "No user message was provided"
            )

        # ----------------------------------------------------
        # Prepare request body
        # ----------------------------------------------------
        #
        # AI server currently expects:
        #
        # {
        #     "message": "..."
        # }
        #
        # We can extend this later with context/messages
        # without changing the provider interface.
        # ----------------------------------------------------

        payload = {
            "message": user_message,
        }

        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        # ----------------------------------------------------
        # Security headers
        # ----------------------------------------------------

        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex

        signature = self._sign_request(
            method="POST",
            path=AI_SERVER_PATH,
            body=body,
            timestamp=timestamp,
            nonce=nonce,
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Server-Signature": signature,
            "X-Request-Timestamp": timestamp,
            "X-Request-Nonce": nonce,
        }

        # ----------------------------------------------------
        # Request
        # ----------------------------------------------------

        try:
            response = await self.client.post(
                f"{self.base_url}{AI_SERVER_PATH}",
                content=body,
                headers=headers,
            )

        except httpx.TimeoutException as exc:
            raise AIProviderUnavailable(
                "AI server timed out"
            ) from exc

        except httpx.ConnectError as exc:
            raise AIProviderUnavailable(
                "Could not connect to AI server"
            ) from exc

        except httpx.HTTPError as exc:
            raise AIProviderUnavailable(
                "AI server request failed"
            ) from exc

        # ----------------------------------------------------
        # HTTP status handling
        # ----------------------------------------------------

        if response.status_code in {401, 403}:
            raise AIProviderUnavailable(
                "AI server rejected authentication"
            )

        if response.status_code >= 500:
            raise AIProviderUnavailable(
                "AI server is unavailable"
            )

        if response.status_code >= 400:
            raise AIProviderRequestError(
                f"AI server returned HTTP {response.status_code}"
            )

        # ----------------------------------------------------
        # Parse response
        # ----------------------------------------------------

        try:
            data = response.json()
        except ValueError as exc:
            raise AIProviderRequestError(
                "AI server returned invalid JSON"
            ) from exc

        content = data.get("response")

        if not isinstance(content, str):
            raise AIProviderRequestError(
                "AI server response is missing 'response'"
            )

        return AICompletion(
            content=content,
            provider=data.get("provider", "remote_ai"),
            model=data.get("model"),
        )

    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    async def close(self) -> None:
        await self.client.aclose()


# ============================================================
# Optional placeholders
# ============================================================

class GeminiProvider(AIProvider):

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        context: list[dict[str, Any]],
    ) -> AICompletion:

        raise AIProviderUnavailable(
            "Gemini provider is not configured"
        )


class LocalModelProvider(AIProvider):

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        context: list[dict[str, Any]],
    ) -> AICompletion:

        raise AIProviderUnavailable(
            "Local model provider is not configured"
        )


# ============================================================
# AI Service
# ============================================================

class AIService:

    def __init__(
        self,
        provider: AIProvider | None = None,
    ):
        self.provider = provider or RemoteAIProvider()

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        context: list[dict[str, Any]],
    ) -> AICompletion:

        return await self.provider.complete(
            messages=messages,
            context=context,
        )