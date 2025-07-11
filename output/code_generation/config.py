import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, HttpUrl

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses Pydantic's BaseSettings for validation and type checking.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Security Testing API"
    API_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field("development", pattern="^(development|testing|production)$")
    DEBUG_MODE: bool = False

    # Database settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL") # e.g., "postgresql+asyncpg://user:password@host:port/dbname"

    # JWT settings
    SECRET_KEY: SecretStr = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    BACKEND_CORS_ORIGINS: List[Union[str, HttpUrl]] = [
        "http://localhost",
        "http://localhost:3000", # Frontend development server
        "http://localhost:8080",
    ]

    # Rate Limiting settings
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    RATE_LIMIT_DEFAULT_TIMES: int = 100
    RATE_LIMIT_DEFAULT_SECONDS: int = 60

    # Admin user credentials for initial setup (for development/testing)
    # In production, these should be managed securely, e.g., via secrets manager
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_PASSWORD: str = "adminpass" # CHANGE THIS IN PRODUCTION!

    # Logging settings
    LOG_LEVEL: str = "INFO" # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Create a singleton instance of settings
settings = Settings()

# Ensure CORS origins are properly formatted for FastAPI
if isinstance(settings.BACKEND_CORS_ORIGINS, list):
    settings.BACKEND_CORS_ORIGINS = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
else:
    settings.BACKEND_CORS_ORIGINS = [str(settings.BACKEND_CORS_ORIGINS)]