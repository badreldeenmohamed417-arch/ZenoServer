import html
import logging
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_url(path: str, **params: str) -> str:
    base = settings.PUBLIC_API_BASE_URL.rstrip("/")
    query = urlencode(params)
    return f"{base}{path}?{query}" if query else f"{base}{path}"


async def _send_brevo_email(
    *,
    to_email: str,
    subject: str,
    html_content: str,
) -> None:
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }

    payload = {
        "sender": {
            "name": settings.SENDER_NAME,
            "email": settings.SENDER_EMAIL,
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            settings.BREVO_API_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()


async def send_reset_code_via_brevo(
    to_email: str,
    token: str,
    language: str = "ar",
) -> None:
    translations = {
        "ar": {
            "subject": "إعادة تعيين كلمة المرور - MasterKey",
            "title": "استعادة كلمة المرور",
            "body": "تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بحسابك. اضغط على الزر أدناه لتعيين كلمة مرور جديدة.",
            "button": "تغيير كلمة المرور",
            "footer": "الرابط صالح لمدة 15 دقيقة فقط. إذا لم تطلب إعادة تعيين كلمة المرور، يمكنك تجاهل هذه الرسالة.",
            "dir": "rtl",
        },
        "en": {
            "subject": "Password Reset - MasterKey",
            "title": "Reset Your Password",
            "body": "We received a request to reset your MasterKey password. Click the button below to choose a new password.",
            "button": "Change password",
            "footer": "This link is valid for 15 minutes. If you did not request a password reset, you can safely ignore this email.",
            "dir": "ltr",
        },
    }

    lang = translations.get(language, translations["ar"])
    reset_link = _build_url("/auth/web/reset-password", token=token)

    subject = lang["subject"]
    title = html.escape(lang["title"])
    body = html.escape(lang["body"])
    button = html.escape(lang["button"])
    footer = html.escape(lang["footer"])

    html_content = f"""
    <!doctype html>
    <html dir="{lang['dir']}" lang="{language}">
      <head>
        <meta charset="UTF-8">
        <title>{title}</title>
      </head>
      <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,sans-serif;">
        <div style="padding:40px 0;">
          <div style="max-width:500px;margin:0 auto;background:#ffffff;border-radius:12px;padding:32px;box-sizing:border-box;">
            <h2 style="margin-top:0;color:#1e293b;">{title}</h2>
            <p style="color:#475569;line-height:1.7;">{body}</p>
            <div style="text-align:center;margin:30px 0;">
              <a href="{html.escape(reset_link, quote=True)}"
                 style="background:#2563eb;color:#fff;padding:13px 24px;border-radius:7px;text-decoration:none;font-weight:700;display:inline-block;">
                {button}
              </a>
            </div>
            <p style="font-size:13px;color:#64748b;line-height:1.6;">{footer}</p>
            <div style="margin-top:28px;text-align:center;color:#94a3b8;font-size:12px;">
              MasterKey © 2026
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    await _send_brevo_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
    )


async def send_login_alert_via_brevo(
    to_email: str,
    device_name: str,
    login_time: str,
    location: str = "Unknown",
    language: str = "ar",
    pending_token: str = "",
) -> None:
    translations = {
        "ar": {
            "subject": "تنبيه أمني: مطلوب تأكيد تسجيل الدخول - MasterKey",
            "title": "مطلوب تأكيد تسجيل الدخول",
            "body": "تلقينا محاولة تسجيل دخول إلى حسابك. يرجى تأكيد ما إذا كنت أنت من قام بها قبل متابعة فتح التطبيق.",
            "device_label": "اسم الجهاز / المدرس",
            "time_label": "وقت محاولة الدخول",
            "location_label": "الموقع",
            "yes_btn": "نعم، تأكيد الدخول",
            "no_btn": "لا، رفض المحاولة",
            "footer": "إذا لم تكن أنت من قام بهذا الإجراء، ارفض المحاولة وغيّر كلمة المرور الخاصة بك.",
            "dir": "rtl",
        },
        "en": {
            "subject": "Security Alert: Login Confirmation Required - MasterKey",
            "title": "Login Confirmation Required",
            "body": "We received a login attempt to your MasterKey account. Please confirm whether it was you before continuing.",
            "device_label": "Device / Teacher",
            "time_label": "Login time",
            "location_label": "Location",
            "yes_btn": "Yes, approve login",
            "no_btn": "No, reject login",
            "footer": "If you did not perform this action, reject the attempt and change your password immediately.",
            "dir": "ltr",
        },
    }

    lang = translations.get(language, translations["ar"])
    yes_link = _build_url("/auth/confirm-login", token=pending_token, action="yes")
    no_link = _build_url("/auth/confirm-login", token=pending_token, action="no")

    def esc(value: str) -> str:
        return html.escape(str(value))

    html_content = f"""
    <!doctype html>
    <html dir="{lang['dir']}" lang="{language}">
      <head><meta charset="UTF-8"><title>{esc(lang['title'])}</title></head>
      <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,sans-serif;">
        <div style="padding:40px 0;">
          <div style="max-width:500px;margin:0 auto;background:#fff;border-radius:12px;padding:32px;box-sizing:border-box;">
            <h2 style="margin-top:0;color:#1e293b;">{esc(lang['title'])}</h2>
            <p style="color:#475569;line-height:1.7;">{esc(lang['body'])}</p>
            <div style="background:#f8fafc;padding:16px 18px;border-radius:8px;border:1px solid #e2e8f0;margin:22px 0;line-height:1.9;">
              <div><strong>{esc(lang['device_label'])}:</strong> {esc(device_name)}</div>
              <div><strong>{esc(lang['time_label'])}:</strong> {esc(login_time)}</div>
              <div><strong>{esc(lang['location_label'])}:</strong> {esc(location)}</div>
            </div>
            <div style="text-align:center;margin:30px 0;">
              <a href="{html.escape(yes_link, quote=True)}" style="background:#16a34a;color:#fff;padding:12px 22px;border-radius:7px;text-decoration:none;font-weight:700;display:inline-block;margin:5px;">{esc(lang['yes_btn'])}</a>
              <a href="{html.escape(no_link, quote=True)}" style="background:#dc2626;color:#fff;padding:12px 22px;border-radius:7px;text-decoration:none;font-weight:700;display:inline-block;margin:5px;">{esc(lang['no_btn'])}</a>
            </div>
            <p style="font-size:13px;color:#64748b;line-height:1.6;">{esc(lang['footer'])}</p>
            <div style="margin-top:28px;text-align:center;color:#94a3b8;font-size:12px;">MasterKey © 2026</div>
          </div>
        </div>
      </body>
    </html>
    """

    await _send_brevo_email(
        to_email=to_email,
        subject=lang["subject"],
        html_content=html_content,
    )
