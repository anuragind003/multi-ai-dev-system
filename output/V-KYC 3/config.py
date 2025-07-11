import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses Pydantic's BaseSettings for robust configuration management.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "VKYC Recording API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database settings
    DATABASE_URL: str = "postgresql+psycopg2://user:password@db:5432/vkyc_db"
    ASYNC_DATABASE_URL: str = "postgresql+asyncpg://user:password@db:5432/vkyc_db" # For async operations

    # JWT Authentication settings
    SECRET_KEY: str = "super-secret-jwt-key-please-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Rate Limiting settings
    RATE_LIMIT_PER_MINUTE: int = 100 # Max requests per minute per IP

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "app.log"

    # NFS Server (example placeholder, actual integration would be more complex)
    NFS_SERVER_BASE_PATH: str = "/mnt/vkyc_recordings"

@lru_cache()
def get_settings():
    """
    Cached function to get application settings.
    Ensures settings are loaded only once.
    """
    return Settings()