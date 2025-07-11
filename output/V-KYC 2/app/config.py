from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union, Optional
import os

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "V-KYC Portal Backend"
    PROJECT_DESCRIPTION: str = "Backend API for managing V-KYC recordings and user access."
    API_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database Settings
    DATABASE_URL: str = "sqlite:///./sql_app.db" # Default to SQLite for easy local setup
    # Example for PostgreSQL: postgresql://user:password@host:port/dbname

    # JWT Settings
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_REPLACE_ME_IN_PROD" # IMPORTANT: Change this in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    # Example for production: ["https://your-frontend-domain.com", "https://your-api-domain.com"]

    # Logging Settings
    LOG_LEVEL: str = "INFO" # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE_PATH: Optional[str] = "app.log" # Set to None to disable file logging

    # Rate Limiting Settings (for basic in-memory middleware)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100

    # Admin User (for initial setup/testing)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "adminpass" # IMPORTANT: Change this in production!

settings = Settings()

# Ensure secret key is not default in production
if settings.SECRET_KEY == "YOUR_SUPER_SECRET_KEY_REPLACE_ME_IN_PROD" and os.getenv("APP_ENV") == "production":
    import warnings
    warnings.warn("WARNING: Default SECRET_KEY is being used in production. This is insecure!")