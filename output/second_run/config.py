import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()  # Load environment variables from .env file

class Settings(BaseSettings):
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "postgresql://user:password@host:port/db")
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = os.environ.get("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "*")  # Comma-separated list of origins
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()