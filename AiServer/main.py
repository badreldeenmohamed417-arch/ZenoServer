from fastapi import FastAPI
from AiServer.api import send_msg

app = FastAPI()

app.include_router(send_msg.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}