from fastapi import FastAPI

# Import reset_password so it registers its routes on auth.router.
from app.api import reset_password  # noqa: F401
from app.api import auth, app_connection, backup, restore, messages, subscription, devices

app = FastAPI(
    title="MasterKey API",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(app_connection.router)
app.include_router(backup.router)
app.include_router(restore.router)
app.include_router(messages.router)
app.include_router(subscription.router)
app.include_router(devices.router)


@app.get("/")
def home():
    return {"status": "running"}


@app.get("/health/live")
def health_live():
    return {"status": "ok"}
