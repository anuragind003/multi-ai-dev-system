import os
from typing import List, Literal
from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "V-KYC Portal Backend"
    API_VERSION: str = "1.0.0"
    DEBUG_MODE: bool = Field(False, description="Enable debug mode for development.")
    PORT: int = Field(8000, description="Port on which the FastAPI application will run.")

    # Database Settings
    DATABASE_URL: PostgresDsn = Field(
        ...,
        description="PostgreSQL database connection URL. Example: postgresql+asyncpg://user:password@host:port/dbname"
    )
    DB_POOL_SIZE: int = Field(20, description="Maximum number of connections in the database pool.")
    DB_MAX_OVERFLOW: int = Field(10, description="Number of connections that can be opened beyond the pool_size.")
    DB_POOL_TIMEOUT: int = Field(30, description="Number of seconds to wait for a connection to become available.")

    # Security Settings
    SECRET_KEY: str = Field(..., min_length=32, description="Secret key for JWT token encoding/decoding.")
    ALGORITHM: str = Field("HS256", description="Algorithm used for JWT signing.")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, description="Access token expiration time in minutes.")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, description="Refresh token expiration time in days (not implemented in this scope but good practice).")

    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        ["*"],
        description="List of allowed origins for CORS. Use ['*'] for all origins (not recommended for production)."
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(True, description="Allow credentials (cookies, authorization headers) to be sent with requests.")
    CORS_ALLOW_METHODS: List[str] = Field(
        ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="List of allowed HTTP methods for CORS."
    )
    CORS_ALLOW_HEADERS: List[str] = Field(
        ["*"],
        description="List of allowed HTTP headers for CORS. Use ['*'] for all headers (not recommended for production)."
    )

    # Logging Settings
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", description="Minimum logging level."
    )
    LOG_FILE_PATH: str = Field(
        "app.log", description="Path to the log file. If empty, logs only to console."
    )

settings = Settings()

# Example of how to load .env file if not using pydantic-settings directly
# from dotenv import load_dotenv
# load_dotenv()