from fastapi import FastAPI
# استيراد كائنات الـ FastAPI الأصلية من ملفاتك الحالية
from AiServer.main import app as ai_app
from MainServer.app.main import app as main_app

# السيرفر الرئيسي (الذي سيعالجه Vercel وتصل إليه الطلبات العامة)
app = FastAPI()

# دمج السيرفرين
app.mount("/ai", ai_app)        # الوصول لـ AiServer سيكون عبر /ai/path
app.mount("/main", main_app)    # الوصول لـ MainServer سيكون عبر /main/path