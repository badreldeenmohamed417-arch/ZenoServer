from fastapi import Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router
from app.core.database import get_db
from app.core.security import validate_password_strength
from app.models.user import User
from app.services.auth_service import AuthService


@router.get("/web/reset-password", response_class=HTMLResponse)
async def reset_password_web_form(token: str):
    token_data = AuthService._reset_tokens_cache.get(token)

    if not token_data:
        return HTMLResponse(
            content="""
            <body style="font-family:Arial;text-align:center;padding:50px;background:#f4f6f8;">
              <h2 style="color:#dc2626;">رابط غير صالح أو منتهي</h2>
              <p>يرجى طلب رابط جديد لإعادة تعيين كلمة المرور.</p>
            </body>
            """,
            status_code=400,
        )

    html_content = f"""
    <!doctype html>
    <html lang="ar" dir="rtl">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>إعادة تعيين كلمة المرور - MasterKey</title>
      </head>
      <body style="font-family:Arial,sans-serif;background:#f4f6f8;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;">
        <div style="background:#fff;padding:30px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,.05);width:100%;max-width:400px;box-sizing:border-box;">
          <h2 style="color:#1e293b;margin-top:0;">إعادة تعيين كلمة المرور</h2>
          <p style="color:#64748b;font-size:14px;line-height:1.7;">أدخل كلمة المرور الجديدة لحسابك في MasterKey.</p>
          <form action="/auth/web/reset-password" method="POST">
            <input type="hidden" name="token" value="{token}">
            <input type="password" name="new_password" placeholder="كلمة المرور الجديدة" required
              style="width:100%;padding:12px;margin:10px 0;border:1px solid #cbd5e1;border-radius:6px;box-sizing:border-box;">
            <button type="submit"
              style="width:100%;padding:12px;background:#2563eb;color:white;border:none;border-radius:6px;font-weight:bold;cursor:pointer;">
              تحديث كلمة المرور
            </button>
          </form>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/web/reset-password", response_class=HTMLResponse)
async def reset_password_web_submit(
    token: str = Form(...),
    new_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    is_valid, errors = validate_password_strength(new_password)
    if not is_valid:
        return HTMLResponse(
            content=(
                "<h3 style='text-align:center;color:red;font-family:Arial;'>"
                f"كلمة المرور ضعيفة: {', '.join(errors)}"
                "</h3>"
            ),
            status_code=400,
        )

    try:
        await AuthService.reset_password(db, token, new_password)
    except ValueError as exc:
        return HTMLResponse(
            content=f"<h3 style='text-align:center;color:red;font-family:Arial;'>{exc}</h3>",
            status_code=400,
        )
    except Exception:
        return HTMLResponse(
            content="<h3 style='text-align:center;color:red;font-family:Arial;'>حدث خطأ غير متوقع.</h3>",
            status_code=500,
        )

    return HTMLResponse(
        content="""
        <body style="font-family:Arial;text-align:center;padding:50px;background:#f4f6f8;">
          <div style="background:#fff;padding:40px;border-radius:12px;display:inline-block;box-shadow:0 4px 12px rgba(0,0,0,.05);">
            <h2 style="color:#16a34a;">تم تغيير كلمة المرور بنجاح!</h2>
            <p style="color:#64748b;">يمكنك الآن إغلاق هذه الصفحة وتسجيل الدخول من تطبيق MasterKey.</p>
          </div>
        </body>
        """
    )
