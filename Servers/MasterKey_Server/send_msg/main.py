from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
import httpx
from pydantic import BaseModel
from database_file import (
    get_chat_id_by_phone,
    get_user_language,
    init_db,
    save_phone_chat,
    save_user_language,
)

from get_tokens import BOT_TOKENS

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager to initialize database tables on startup."""
    await init_db()
    print("Database initialization complete.")
    yield


app = FastAPI(title="Telegram Multi-Bot Service", lifespan=lifespan)


class SendMessagePayload(BaseModel):
    phone_numbers: list[str]
    text: str


async def call_telegram_api(token: str, method: str, payload: dict) -> dict:
    """Helper method to execute HTTP POST requests to Telegram API."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=payload)
            return response.json()
        except Exception as e:
            print(f"Failed to execute Telegram API request ({method}): {e}")
            return {}


async def send_single_message_fallback(chat_id: str, text: str) -> bool:
    """Attempt sending message via Primary bot, falling back to backups on failure."""
    for index, token in enumerate(BOT_TOKENS):
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        res = await call_telegram_api(token, "sendMessage", payload)
        if res.get("ok"):
            return True  # Sent successfully

        print(
            f"Bot index {index} failed for chat_id {chat_id}. Attempting next bot..."
        )

    return False  # All bots failed


# ------------------------------------------------------------------
# 📤 Endpoint invoked by the Main Server to send notifications
# ------------------------------------------------------------------
@app.post("/send")
async def send_messages(payload: SendMessagePayload):
    """Dispatch messages to a list of phone numbers with automatic bot fallback."""
    successful = 0
    failed = 0
    not_registered = 0

    for phone in payload.phone_numbers:
        chat_id = await get_chat_id_by_phone(phone)
        if not chat_id:
            not_registered += 1
            continue

        is_sent = await send_single_message_fallback(chat_id, payload.text)
        if is_sent:
            successful += 1
        else:
            failed += 1

    return {
        "success": True,
        "delivered": successful,
        "failed": failed,
        "not_registered": not_registered,
    }


# ------------------------------------------------------------------
# 📥 Webhook endpoint handling user onboarding (/start & contact)
# ------------------------------------------------------------------
@app.post("/webhook/{bot_index}")
async def telegram_webhook(bot_index: int, request: Request):
    """Unified webhook endpoint handling updates across all bots."""
    if bot_index < 0 or bot_index >= len(BOT_TOKENS):
        return {"status": "invalid_bot_index"}

    token = BOT_TOKENS[bot_index]
    data = await request.json()

    # 1. Handle Language Selection via Callback Query
    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id = str(cb["message"]["chat"]["id"])
        cb_id = cb["id"]
        cb_data = cb.get("data", "")

        await call_telegram_api(
            token, "answerCallbackQuery", {"callback_query_id": cb_id}
        )

        if cb_data in ["lang_ar", "lang_en"]:
            selected_lang = "ar" if cb_data == "lang_ar" else "en"
            await save_user_language(chat_id, selected_lang)

            if selected_lang == "ar":
                msg_text = "أهلاً بك! 🖐️\nيرجى الضغط على الزر أدناه لمشاركة رقم هاتفك وتفعيل التنبيهات:"
                btn_text = "📱 مشاركة رقم الهاتف"
            else:
                msg_text = "Welcome! 🖐️\nPlease click the button below to share your phone number and activate notifications:"
                btn_text = "📱 Share Phone Number"

            contact_payload = {
                "chat_id": chat_id,
                "text": msg_text,
                "reply_markup": {
                    "keyboard": [[{"text": btn_text, "request_contact": True}]],
                    "resize_keyboard": True,
                    "one_time_keyboard": True,
                },
            }
            await call_telegram_api(token, "sendMessage", contact_payload)

        return {"status": "ok"}

    if "message" not in data:
        return {"status": "ok"}

    message = data["message"]
    chat_id = str(message["chat"]["id"])

    # 2. Handle /start Command -> Present Language Selection Buttons
    if "text" in message and message["text"].startswith("/start"):
        lang_payload = {
            "chat_id": chat_id,
            "text": "برجاء اختيار اللغة / Please select your language:",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "العربية 🇪🇬", "callback_data": "lang_ar"},
                        {"text": "English 🇬🇧", "callback_data": "lang_en"},
                    ]
                ]
            },
        }
        await call_telegram_api(token, "sendMessage", lang_payload)

    # 3. Handle Contact Sharing -> Save Phone, Chat ID & Language
    elif "contact" in message:
        phone_number = message["contact"]["phone_number"]
        user_lang = await get_user_language(chat_id)

        await save_phone_chat(
            phone_number=phone_number,
            chat_id=chat_id,
            language=user_lang,
        )

        if user_lang == "ar":
            confirm_text = f"✅ تم حفظ رقم الهاتف ({phone_number}) بنجاح!\nستصلك الإشعارات هنا."
        else:
            confirm_text = f"✅ Phone number ({phone_number}) saved successfully!\nYou will receive notifications here."

        confirm_payload = {
            "chat_id": chat_id,
            "text": confirm_text,
            "reply_markup": {"remove_keyboard": True},
        }
        await call_telegram_api(token, "sendMessage", confirm_payload)

    return {"status": "ok"}