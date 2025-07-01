from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@host:port/database"
    API_KEY: str = "your_api_key"

    class Config:
        env_file = ".env"

settings = Settings()