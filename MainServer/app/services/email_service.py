import html
from urllib.parse import urlencode
import httpx
from app.core.config import settings


def _url(path: str, **params: str) -> str:
    return f"{settings.PUBLIC_API_BASE_URL.rstrip('/')}{path}?{urlencode(params)}"


async def _send(to_email: str, subject: str, html_content: str) -> None:
    if not settings.BREVO_API_KEY:
        raise RuntimeError("Brevo is not configured")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            settings.BREVO_API_URL,
            headers={
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json",
            },
            json={
                "sender": {
                    "name": settings.SENDER_NAME,
                    "email": settings.SENDER_EMAIL,
                },
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content,
            },
        )
        response.raise_for_status()


def _build_email_template(
        *,
        title: str,
        greeting: str,
        message: str,
        button_text: str,
        button_url: str,
        footer_note: str,
        is_arabic: bool = True,
) -> str:
    direction = "rtl" if is_arabic else "ltr"
    align = "right" if is_arabic else "left"
    font_family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"

    return f"""
    <!DOCTYPE html>
    <html lang="{'ar' if is_arabic else 'en'}" dir="{direction}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f6f9; font-family: {font_family}; direction: {direction}; text-align: {align};">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed; background-color: #f4f6f9; padding: 40px 0;">
            <tr>
                <td align="center">
                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 520px; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); overflow: hidden;">

                        <!-- Header -->
                        <tr>
                            <td style="padding: 32px 32px 24px 32px; background-color: #0f172a; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 26px; font-weight: 700; letter-spacing: 0.5px;">Zeno</h1>
                            </td>
                        </tr>

                        <!-- Body Content -->
                        <tr>
                            <td style="padding: 32px; color: #334155; font-size: 15px; line-height: 1.6;">
                                <h2 style="margin: 0 0 16px 0; color: #0f172a; font-size: 20px; font-weight: 600;">{greeting}</h2>
                                <p style="margin: 0 0 24px 0; color: #475569;">{message}</p>

                                <!-- CTA Button -->
                                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin: 28px 0;">
                                    <tr>
                                        <td align="center">
                                            <a href="{button_url}" target="_blank" style="display: inline-block; padding: 14px 32px; background-color: #2563eb; color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 600; border-radius: 8px; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2); transition: background-color 0.2s;">
                                                {button_text}
                                            </a>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Secondary Link fallback -->
                                <p style="margin: 24px 0 0 0; font-size: 12px; color: #94a3b8; word-break: break-all;">
                                    {"إذا لم يعمل الزر، انسخ الرابط ورسخه في المتصفح:" if is_arabic else "If the button doesn't work, copy and paste this link:"}<br>
                                    <a href="{button_url}" style="color: #2563eb; text-decoration: underline;">{button_url}</a>
                                </p>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding: 20px 32px; background-color: #f8fafc; border-top: 1px solid #f1f5f9; text-align: center; color: #64748b; font-size: 13px;">
                                <p style="margin: 0 0 8px 0;">{footer_note}</p>
                                <p style="margin: 0; font-size: 12px; color: #94a3b8;">&copy; Zeno. All rights reserved.</p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


async def send_password_reset(to_email: str, token: str, language: str = "ar") -> None:
    # استخدام الرابط المطلوب مع الـ token
    raw_link = f"http://www.nexorai/reset-code-page?token={token}"
    link = html.escape(raw_link, quote=True)

    is_arabic = language == "ar"
    subject = "إعادة تعيين كلمة المرور - Zeno" if is_arabic else "Reset your Zeno password"

    html_content = _build_email_template(
        title=subject,
        greeting="مرحباً بك،" if is_arabic else "Hello,",
        message=(
            "تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بحسابك على Zeno. يمكنك تعيين كلمة مرور جديدة بالضغط على الزر أدناه:"
            if is_arabic
            else "We received a request to reset your password for your Zeno account. Click the button below to set a new one:"
        ),
        button_text="إعادة تعيين كلمة المرور" if is_arabic else "Reset Password",
        button_url=link,
        footer_note=(
            "صلاحية هذا الرابط 15 دقيقة فقط. إذا لم تطلب إعادة التعيين، يمكنك تجاهل هذا البريد وآمان حسابك محمي."
            if is_arabic
            else "This link expires in 15 minutes. If you didn't request a reset, you can ignore this email."
        ),
        is_arabic=is_arabic,
    )

    await _send(to_email, subject, html_content)


async def send_email_verification(to_email: str, token: str, language: str = "ar") -> None:
    # استخدام الرابط المطلوب مع الـ token
    raw_link = f"http://www.nexorai/verify-email-page?token={token}"
    link = html.escape(raw_link, quote=True)

    is_arabic = language == "ar"
    subject = "تأكيد البريد الإلكتروني - Zeno" if is_arabic else "Verify your Zeno email"

    html_content = _build_email_template(
        title=subject,
        greeting="أهلاً بك في Zeno!" if is_arabic else "Welcome to Zeno!",
        message=(
            "شكراً لتسجيلك معنا! يرجى تأكيد بريدك الإلكتروني لتفعيل حسابك بالكامل والاستفادة من كافة مميزات المنصة."
            if is_arabic
            else "Thanks for signing up! Please verify your email address to fully activate your account and access all features."
        ),
        button_text="تأكيد البريد الإلكتروني" if is_arabic else "Verify Email Address",
        button_url=link,
        footer_note=(
            "صلاحية هذا الرابط 24 ساعة. إذا لم تقم بإنشاء حساب على Zeno، يرجى تجاهل هذا البريد."
            if is_arabic
            else "This link is valid for 24 hours. If you did not create a Zeno account, please ignore this email."
        ),
        is_arabic=is_arabic,
    )

    await _send(to_email, subject, html_content)


async def send_security_notification(*args, **kwargs) -> None:
    raise NotImplementedError("Security notifications are not enabled in V1")