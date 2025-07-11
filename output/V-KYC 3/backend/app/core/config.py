from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    # Project settings
    PROJECT_NAME: str = "FastAPI Monolith"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Monolithic application with FastAPI backend and placeholder frontend."
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development" # development, staging, production

    # Database settings
    DATABASE_URL: str = "postgresql+psycopg2://user:password@db:5432/mydatabase"

    # Security settings
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_REPLACE_ME" # pragma: allowlist secret
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"] # Example origins

    # Monitoring settings
    PROMETHEUS_METRICS_PATH: str = "/metrics"

    # Docker settings (for local development/testing)
    DOCKER_DB_HOST: str = "db"

    # Configuration for Pydantic Settings
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env.backend'),
        env_file_encoding='utf-8',
        extra='ignore' # Ignore extra environment variables not defined here
    )

settings = Settings()

# Ensure secret key is not default in production
if settings.ENVIRONMENT == "production" and settings.SECRET_KEY == "YOUR_SUPER_SECRET_KEY_REPLACE_ME":
    raise ValueError("SECRET_KEY must be set to a strong, unique value in production environment.")