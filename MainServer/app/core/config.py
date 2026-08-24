from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# /home/badr-eldeen/Documents/ZenoServer/MainServer
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str

    # Backblaze B2
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET_NAME: str = ""
    B2_ENDPOINT_URL: str = ""

    # Redis / Dramatiq
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379

    # Brevo
    BREVO_API_KEY: str = ""
    BREVO_API_URL: str = "https://api.brevo.com/v3/smtp/email"
    SENDER_EMAIL: str = "noreply@zeno.local"
    SENDER_NAME: str = "Zeno"

    # Public URL
    PUBLIC_API_BASE_URL: str = "http://127.0.0.1:8000"
    PASSWORD_RESET_URL: str = (
        "http://127.0.0.1:3000/reset-password"
    )

    # Application limits
    PASSWORD_RESET_TTL_SECONDS: int = 15 * 60
    PASSWORD_RESET_MIN_INTERVAL_SECONDS: int = 60
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    DEFAULT_FREE_PLAN_TOKENS: int = 1000
    AI_MESSAGE_TOKEN_COST: int = 10

    SERVER_TO_SERVER_SECRET: str

    # Google
    GOOGLE_CLIENT_ID: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()