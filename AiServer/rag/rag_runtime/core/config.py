from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .paths import storage_path, storage_root


ENV_FILE = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    # Gemini
    GEMINI_API_KEY: str | None = None
    GEMINI_GENERATION_MODEL: str = "gemini-flash-lite-latest"
    GEMINI_VERIFIER_MODEL: str = "gemini-flash-lite-latest"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_EMBEDDING_DIMENSION: int = 768

    # Vector / Storage
    VECTOR_BACKEND: str = "sqlite"

    SQLITE_PATH: Path = Field(
        default_factory=lambda: storage_path("zeno.db")
    )

    STORAGE_DIR: Path = Field(
        default_factory=storage_root
    )

    # Logging
    LOG_LEVEL: str = "INFO"

    # Server-to-server authentication
    SERVER_TO_SERVER_SECRET: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()