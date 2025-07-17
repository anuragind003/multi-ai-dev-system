import os
from typing import List, Union
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses Pydantic's BaseSettings for validation and type checking.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Project Metadata
    PROJECT_NAME: str = "VKYC Recording Portal Backend"
    PROJECT_DESCRIPTION: str = "API for managing and accessing VKYC recording metadata and files."
    API_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG_MODE: bool = False

    # Database Settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL", description="PostgreSQL database connection URL")

    # Security Settings
    SECRET_KEY: str = Field(..., env="SECRET_KEY", description="Secret key for JWT token signing")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS Origins
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        ["http://localhost:3000", "http://localhost:8000"],
        env="BACKEND_CORS_ORIGINS",
        description="Comma-separated list of allowed CORS origins for the frontend."
    )

    # Trusted Hosts
    TRUSTED_HOSTS: List[str] = Field(
        ["localhost", "127.0.0.1"],
        env="TRUSTED_HOSTS",
        description="Comma-separated list of trusted hostnames for the application."
    )

    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "app.log"

    # NFS Server Settings (Example, replace with actual NFS client logic)
    NFS_MOUNT_POINT: str = Field("/mnt/vkyc_recordings", env="NFS_MOUNT_POINT", description="Local mount point for NFS server.")
    # Note: Direct NFS access from a web server is generally not recommended for security/performance.
    # A dedicated file service or proxy might be better. This is a placeholder.

    # Admin User (for initial setup/testing)
    ADMIN_EMAIL: str = Field("admin@example.com", env="ADMIN_EMAIL", description="Default admin user email.")
    ADMIN_PASSWORD: str = Field("adminpassword", env="ADMIN_PASSWORD", description="Default admin user password.")
    # IMPORTANT: In production, do not hardcode default admin credentials.
    # Use environment variables or a secure secrets management system.

    # Rate Limiting (SlowAPI)
    RATE_LIMIT_DEFAULT: str = "100/minute" # Default rate limit for endpoints

    class Config:
        """Pydantic configuration for the Settings class."""
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create a settings instance to be imported throughout the application
settings = Settings()

# Example of how to load .env file for local development
# if not os.getenv("DATABASE_URL"):
#     from dotenv import load_dotenv
#     load_dotenv()