from fastapi import FastAPI

from app.api import auth, chat, health, payments, subscription, tokens, users

app = FastAPI(title="Zeno API", version="1.0.0")

for router in (
    auth.router,
    users.router,
    chat.router,
    subscription.router,
    tokens.router,
    payments.router,
    health.router,
):
    app.include_router(router)
