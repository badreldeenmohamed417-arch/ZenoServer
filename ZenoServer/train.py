import httpx
from fastapi import HTTPException

BrevoApi="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"
BREVO_API_URL="https://api.brevo.com/v3/smtp/email"
SENDER_EMAIL="suppoer@nexorai.top"
SENDER_NAME="MasterKey"

async def send_reset_code_via_brevo(to_email: str, code: str, language: str = "ar"):
    translations = {
        "ar": {
            "subject": "إعادة تعيين كلمة المرور - MasterKey",
            "title": "استعادة كلمة المرور",
            "body": "مرحباً، تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بحسابك. يمكنك استخدام كود التحقق أدناه لإتمام العملية:",
            "code_label": "كود التحقق",
            "footer_note": "هذا الكود صالح لمدة 15 دقيقة فقط. إذا لم تقم بهذا الطلب، يمكنك تجاهل هذه الرسالة بأمان ولن يتم إجراء أي تغيير على حسابك.",
            "copyright": "جميع الحقوق محفوظة",
            "dir": "rtl"
        },
        "en": {
            "subject": "Password Reset - MasterKey",
            "title": "Reset Your Password",
            "body": "Hello, we received a request to reset your password. Use the verification code below to complete the process:",
            "code_label": "Verification Code",
            "footer_note": "This code is valid for 15 minutes only. If you didn't request this, you can safely ignore this email and no changes will be made to your account.",
            "copyright": "All rights reserved",
            "dir": "ltr"
        }
    }

    lang = translations.get(language, translations["ar"])

    html_content = f"""
        <html>
            <head>
                <style>@import url('');</style>
            </head>
            <body style="margin: 0; padding: 0; background-color: #f4f6f8; font-family: 'Cairo', sans-serif;">
                <div dir="{lang['dir']}" style="background-color: #f4f6f8; padding: 40px 0;">
                    <div style="max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">

                        <!-- Header with Logo -->
                        <div style="background: linear-gradient(135deg, #0ea5e9, #2563eb); padding: 25px; text-align: center;">
                            <img src="https://yourdomain.com/path-to-your-logo.png" alt="MasterKey Logo" style="max-width: 140px; height: auto; display: block; margin: 0 auto;" />
                        </div>

                        <!-- Body Content -->
                        <div style="padding: 30px; text-align: {'right' if lang['dir'] == 'rtl' else 'left'}; color: #334155;">
                            <h2 style="margin-top: 0; font-family: 'Cairo', sans-serif;">{lang['title']}</h2>
                            <p style="font-family: 'Cairo', sans-serif; line-height: 1.6;">{lang['body']}</p>

                            <!-- Verification Code Box -->
                            <div style="text-align: center; margin: 25px 0;">
                                <div style="font-size: 32px; font-weight: 800; color: #2563eb; background: #f8fafc; padding: 15px; border-radius: 8px; border: 1.5px dashed #cbd5e1; letter-spacing: 6px;">
                                    {code}
                                </div>
                            </div>

                            <p style="font-size: 13px; color: #64748b; font-family: 'Cairo', sans-serif; line-height: 1.5;">{lang['footer_note']}</p>
                        </div>

                        <!-- Footer -->
                        <div style="background: #f8fafc; padding: 15px; text-align: center; color: #94a3b8; font-size: 12px; font-family: 'Cairo', sans-serif;">
                            {lang['copyright']} &copy; 2026 MasterKey
                        </div>

                    </div>
                </div>
            </body>
        </html>
        """

    headers = {
        "accept": "application/json",
        "api-key": BrevoApi,
        "content-type": "application/json"
    }

    payload = {
        "sender": {
            "name": SENDER_NAME,
            "email": SENDER_EMAIL
        },
        "to": [
            {
                "email": to_email
            }
        ],
        "subject": "إعادة تعيين كلمة المرور - MasterKey",
        "htmlContent": html_content
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(BREVO_API_URL, json=payload, headers=headers)
        if response.status_code != 201:
            raise HTTPException(status_code=500, detail="Failed to send email via Brevo")

import asyncio

async def main():
    # جرب إيميلك الشخصي والكود التجريبي هنا
    await send_reset_code_via_brevo("b16405138@gmail.com", "123456", "en")
    print("Email sent successfully!")

if __name__ == "__main__":
    asyncio.run(main())

