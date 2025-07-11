import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    APP_NAME: str = "FastAPI Monitoring App"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO" # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # Database settings (example)
    DATABASE_URL: str = "postgresql://user:password@db:5432/mydatabase"

    # Security settings (example)
    SECRET_KEY: str = "your-super-secret-key-for-production"
    ALLOWED_HOSTS: str = "*" # Comma-separated list of allowed hosts

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Configure basic logging for initial setup, JSON logging is handled in main.py
logging.basicConfig(level=settings.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')