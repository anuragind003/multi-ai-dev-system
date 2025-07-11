from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses Pydantic's BaseSettings for robust configuration management.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core Application Settings
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "your_super_secret_key_for_fastapi_jwt_or_other_crypto_operations_CHANGE_ME_IN_PROD"

    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/mydatabase"

    # CORS Settings
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000" # Comma-separated list of allowed origins

    # Logging Settings (example)
    LOG_LEVEL: str = "INFO"

    # Add more settings as needed, e.g., for external services, API keys, etc.
    # EXAMPLE_API_KEY: Optional[str] = None

settings = Settings()