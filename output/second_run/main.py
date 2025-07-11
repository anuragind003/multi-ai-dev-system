python
### FILE: config.py
import os
from typing import List
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    app_name: str = "Task Management API"
    environment: str = "development"
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    CORS_ORIGINS: List[str] = ["*"]  # Allow all origins by default; restrict in production

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, tuple)):
            return [str(i).strip() for i in v]
        return ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings():
    return Settings()