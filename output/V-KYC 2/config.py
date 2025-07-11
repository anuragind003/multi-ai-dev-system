import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses Pydantic-Settings for robust configuration management.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "VKYC RBAC Portal"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG_MODE: bool = False

    # Database settings
    DATABASE_URL: str = "postgresql+psycopg2://user:password@db:5432/vkyc_db"

    # JWT settings
    SECRET_KEY: str = "super-secret-key-replace-with-strong-random-one-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"

    # Security headers
    X_FRAME_OPTIONS: str = "DENY"
    X_CONTENT_TYPE_OPTIONS: str = "nosniff"
    X_XSS_PROTECTION: str = "1; mode=block"
    STRICT_TRANSPORT_SECURITY: str = "max-age=31536000; includeSubDomains; preload"
    REFERRER_POLICY: str = "no-referrer-when-downgrade"

settings = Settings()

# Ensure secret key is not default in production
if settings.ENVIRONMENT == Environment.PRODUCTION and \
   settings.SECRET_KEY == "super-secret-key-replace-with-strong-random-one-in-prod":
    raise ValueError("SECRET_KEY must be changed from default in production environment!")