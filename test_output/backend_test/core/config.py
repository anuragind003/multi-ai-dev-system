"""
Application Configuration
"""

import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "General Backend"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://user:password@localhost/dbname"
    
    # Security
    secret_key: str = "your-secret-key-here"
    access_token_expire_minutes: int = 30
    
    # External Services
    redis_url: str = "redis://localhost:6379"
    
    # Monitoring
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
