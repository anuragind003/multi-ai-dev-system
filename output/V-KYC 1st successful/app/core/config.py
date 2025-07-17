from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "VKYC Bulk Download API"
    API_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG_MODE: bool = False

    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@db:5432/vkyc_db"
    ASYNC_DB_POOL_SIZE: int = 10
    ASYNC_DB_MAX_OVERFLOW: int = 20

    # Security settings
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_CHANGE_ME_IN_PROD"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    # Example: BACKEND_CORS_ORIGINS = ["*"] for development, or specific domains in production

    # Rate Limiting
    RATE_LIMIT_CALLS_PER_MINUTE: int = 100

    # File Storage (NFS simulation)
    NFS_BASE_PATH: str = "/mnt/vkyc_recordings" # Simulated NFS mount point

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "app.log"

settings = Settings()