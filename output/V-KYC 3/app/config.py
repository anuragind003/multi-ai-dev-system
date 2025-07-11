import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses Pydantic's BaseSettings for validation and type safety.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "V-KYC Audit Portal Backend"
    PROJECT_DESCRIPTION: str = "Backend API for managing V-KYC recordings, bulk operations, and user access."
    API_VERSION: str = "1.0.0"

    DEBUG_MODE: bool = False

    # Database settings
    DATABASE_URL: str = "postgresql+psycopg2://user:password@db:5432/vkyc_db"
    ECHO_SQL: bool = False # Set to True to log all SQL queries

    # JWT settings
    SECRET_KEY: str = "super-secret-key-replace-with-strong-random-one-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    CORS_ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"] # Frontend URL

    # Rate Limiting settings
    RATE_LIMIT_PER_MINUTE: int = 100 # Max requests per minute globally

    # Admin User for initial setup
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "adminpassword" # CHANGE THIS IN PRODUCTION!

    # NFS Server Simulation (for demonstration)
    NFS_SERVER_PATH: str = "/tmp/vkyc_recordings" # Path to simulate NFS storage

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "app.log"

settings = Settings()

# Ensure NFS_SERVER_PATH exists for simulation
if not os.path.exists(settings.NFS_SERVER_PATH):
    os.makedirs(settings.NFS_SERVER_PATH)
    print(f"Created NFS simulation directory: {settings.NFS_SERVER_PATH}")