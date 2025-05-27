from typing import Generator

from fastapi import HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pydantic_settings import BaseSettings, SettingsConfigDict


# 1. Configuration Management
class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """
    DATABASE_URL: str = "postgresql://user:password@host:5432/cdp_db"
    API_KEY: str = "super_secret_api_key_for_external_integrations"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# 2. Database Session Dependency
# SQLAlchemy engine setup
# pool_pre_ping=True helps maintain healthy connections in the pool
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# SessionLocal is a factory for new Session objects
# autocommit=False and autoflush=False ensure explicit commit/flush for transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a SQLAlchemy database session.
    The session is automatically closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 3. API Key Authentication Dependency
# Define the API Key header name for external integrations
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


def get_api_key(api_key: str = Depends(api_key_header)) -> str:
    """
    Dependency to validate the API key provided in the 'X-API-Key' header.
    This is used for securing external API integrations (e.g., Insta/E-aggregators).
    Raises HTTPException if the provided API key does not match the configured key.
    """
    if api_key == settings.API_KEY:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )