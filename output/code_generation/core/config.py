import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, Field

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Test Management API"
    API_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # Database settings
    POSTGRES_SERVER: str = Field(..., description="PostgreSQL database server host")
    POSTGRES_USER: str = Field(..., description="PostgreSQL database user")
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL database password")
    POSTGRES_DB: str = Field(..., description="PostgreSQL database name")
    DATABASE_URL: str = "" # This will be set dynamically

    # JWT settings
    SECRET_KEY: str = Field(..., min_length=32, description="Secret key for JWT token encryption")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    # CORS settings
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Constructs the async database URL for SQLAlchemy."""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    def __init__(self, **values):
        super().__init__(**values)
        # Set DATABASE_URL dynamically after other fields are loaded
        self.DATABASE_URL = self.ASYNC_DATABASE_URL

# Instantiate settings
settings = Settings()

# Example of how to load CORS origins from an environment variable
# e.g., BACKEND_CORS_ORIGINS="http://localhost:3000,https://example.com"
if os.getenv("BACKEND_CORS_ORIGINS"):
    settings.BACKEND_CORS_ORIGINS = [
        AnyHttpUrl(url.strip()) for url in os.getenv("BACKEND_CORS_ORIGINS").split(",")
    ]
else:
    # Default for development
    settings.BACKEND_CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]