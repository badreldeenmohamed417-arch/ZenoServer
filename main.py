import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.extend([str(BASE_DIR), str(BASE_DIR / "MainServer")])

from fastapi import FastAPI
from MainServer.app.main import app as main_app
from AiServer.main import app as ai_app

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Server is running successfully!"}

app.mount("/main", main_app)
app.mount("/ai", ai_app)