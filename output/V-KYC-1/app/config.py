import logging
from typing import List, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.middleware.cors import CORSMiddleware

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    APP_NAME: str = "V-KYC Recording Portal"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL database connection URL")

    # JWT Authentication
    SECRET_KEY: str = Field(..., min_length=32, description="Secret key for JWT encoding/decoding")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security
    CORS_ORIGINS: str = Field(
        "http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed CORS origins"
    )
    CORS_MIDDLEWARE_CLASS = CORSMiddleware # Can be changed if needed
    RATE_LIMIT_PER_MINUTE: int = 100 # Max requests per minute per IP

    # External Service Paths
    NFS_RECORDINGS_PATH: str = Field(
        "/mnt/nfs/vkyc_recordings",
        description="Absolute path to the NFS mount point for V-KYC recordings"
    )

    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """Converts the comma-separated CORS_ORIGINS string to a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]

    def configure_logging(self):
        """Configures the root logger based on settings."""
        logging.basicConfig(level=self.LOG_LEVEL, format=self.LOG_FORMAT)
        if self.ENVIRONMENT == "production":
            # In production, you might want to send logs to a centralized system
            # e.g., via a logging handler like SysLogHandler, Sentry, ELK stack.
            # For now, just ensure INFO level is default.
            pass

settings = Settings()
settings.configure_logging() # Apply logging configuration on startup