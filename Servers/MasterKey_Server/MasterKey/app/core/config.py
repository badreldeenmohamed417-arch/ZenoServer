from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str

    # Backblaze B2 (S3-compatible)
    B2_KEY_ID: str
    B2_APPLICATION_KEY: str
    B2_BUCKET_NAME: str
    B2_ENDPOINT_URL: str

    # Device authentication
    DEVICE_SECRET_TTL_DAYS: int = 30
    CHALLENGE_TTL_SECONDS: int = 120

    # Redis / Dramatiq
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379

    # Brevo
    BREVO_API_KEY: str = Field(
        validation_alias=AliasChoices("BREVO_API_KEY", "BrevoApi")
    )
    BREVO_API_URL: str = "https://api.brevo.com/v3/smtp/email"
    SENDER_EMAIL: str
    SENDER_NAME: str

    # Public URL used in email links
    PUBLIC_API_BASE_URL: str = "http://127.0.0.1:8000"

    # Application limits
    PASSWORD_RESET_TTL_SECONDS: int = 15 * 60
    LOGIN_APPROVAL_TTL_SECONDS: int = 5 * 60
    PASSWORD_RESET_MIN_INTERVAL_SECONDS: int = 60
    LOGIN_INITIATE_MIN_INTERVAL_SECONDS: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
