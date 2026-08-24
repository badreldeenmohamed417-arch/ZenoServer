import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.extend([str(BASE_DIR), str(BASE_DIR / "MainServer")])

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from MainServer.app.main import app as main_app
from AiServer.main import app as ai_app

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Server is running successfully!"}


# صفحة تغيير كلمة المرور
@app.get("/reset-password-page", response_class=HTMLResponse)
async def reset_password_page():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Reset Password</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f3f4f6; margin: 0; }
        .box { background: white; padding: 25px; border-radius: 8px; text-align: center; width: 320px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        input { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px; }
        button { width: 100%; padding: 10px; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #1d4ed8; }
        #msg { margin-top: 15px; font-weight: bold; font-size: 14px; }
    </style>
</head>
<body>
    <div class="box">
        <h3>Reset Password</h3>
        <input type="password" id="p1" placeholder="New Password">
        <input type="password" id="p2" placeholder="Confirm Password">
        <button onclick="resetPassword()">Submit</button>
        <div id="msg"></div>
    </div>

    <script>
        async function resetPassword() {
            const token = new URLSearchParams(window.location.search).get('token');
            const p1 = document.getElementById('p1').value;
            const p2 = document.getElementById('p2').value;
            const msg = document.getElementById('msg');

            if (!token) {
                msg.innerText = "Error: Missing token in URL!";
                msg.style.color = "red";
                return;
            }

            if (p1 !== p2) {
                msg.innerText = "Passwords do not match!";
                msg.style.color = "red";
                return;
            }

            if (p1.length < 8) {
                msg.innerText = "Password must be at least 8 characters.";
                msg.style.color = "red";
                return;
            }

            msg.innerText = "Processing...";
            msg.style.color = "black";

            try {
                // الاتصال بـ endpoint الخاص بالـ main_app مباشرة عبر المسار الصحيح
                const res = await fetch('/main/auth/reset-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token: token, new_password: p1 })
                });

                if (res.ok) {
                    msg.innerText = "Password changed successfully!";
                    msg.style.color = "green";
                } else {
                    const data = await res.json();
                    msg.innerText = data.detail || "Link is invalid or expired!";
                    msg.style.color = "red";
                }
            } catch (err) {
                msg.innerText = "Server connection error!";
                msg.style.color = "red";
            }
        }
    </script>
</body>
</html>
"""


# صفحة تأكيد البريد الإلكتروني
@app.get("/verify-email-page", response_class=HTMLResponse)
async def verify_email_page():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Email Verification</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f3f4f6; margin: 0; }
        .box { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
        h2 { margin: 0; color: #333; font-size: 22px; }
    </style>
</head>
<body>
    <div class="box">
        <h2 id="status">Verifying...</h2>
    </div>

    <script>
        async function verifyEmail() {
            const token = new URLSearchParams(window.location.search).get('token');
            const status = document.getElementById('status');

            if (!token) {
                status.innerText = "Error: Missing token in URL!";
                status.style.color = "red";
                return;
            }

            try {
                // الاتصال بـ endpoint الخاص بالـ main_app مباشرة عبر المسار الصحيح
                const res = await fetch('/main/auth/verify-email', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token: token })
                });

                if (res.ok) {
                    status.innerText = "Verified! Your email has been successfully verified.";
                    status.style.color = "green";
                } else {
                    const data = await res.json();
                    status.innerText = data.detail || "Verification failed, link may have expired.";
                    status.style.color = "red";
                }
            } catch (err) {
                status.innerText = "Server connection error!";
                status.style.color = "red";
            }
        }

        verifyEmail();
    </script>
</body>
</html>
"""


app.mount("/main", main_app)
app.mount("/ai", ai_app)