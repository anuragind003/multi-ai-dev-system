from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Literal, Optional

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses Pydantic's BaseSettings for validation and type safety.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "V-KYC Portal Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/vkyc_db"

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000"] # Default for development
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Rate Limiting settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100

    # Logging settings
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FILE: Optional[str] = None # If None, logs to console only

settings = Settings()