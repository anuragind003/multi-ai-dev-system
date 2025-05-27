from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

# Load environment variables from .env file
# This should be called as early as possible in your application's startup.
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    This class uses Pydantic's BaseSettings to manage configuration,
    providing type validation and easy access to environment variables.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Application Core Settings ---
    APP_NAME: str = "LTFS Offer CDP"
    API_V1_STR: str = "/api/v1"
    # SECRET_KEY is crucial for security (e.g., JWTs, session management).
    # In production, this should be a strong, randomly generated string
    # and never hardcoded or defaulted to a weak value.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-for-development-only-change-this-in-prod")
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development") # e.g., development, staging, production

    # --- Database Settings (PostgreSQL) ---
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_NAME: str = os.getenv("DB_NAME", "ltfs_cdp_db")

    @property
    def DATABASE_URL(self) -> str:
        """
        Constructs the database connection URL for SQLAlchemy.
        Uses psycopg2 as the driver.
        """
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # --- Data Retention Policies (from BRD NFRs) ---
    # NFR9: Offer history for the past 6 months shall be maintained.
    OFFER_HISTORY_RETENTION_MONTHS: int = 6
    # NFR10: All data in LTFS Offer CDP shall be maintained for previous 3 months before deletion.
    CDP_DATA_RETENTION_MONTHS: int = 3

    # --- File Paths / Directories ---
    # These directories will be used for storing generated files and uploaded files.
    # Ensure these paths are configured correctly for your deployment environment.
    MOENGAGE_FILE_DIR: str = os.getenv("MOENGAGE_FILE_DIR", "data/moengage_files")
    UPLOAD_FILE_DIR: str = os.getenv("UPLOAD_FILE_DIR", "data/uploads")
    DOWNLOAD_FILE_DIR: str = os.getenv("DOWNLOAD_FILE_DIR", "data/downloads") # For unique, duplicate, error files
    EDW_DATA_EXPORT_PATH: str = os.getenv("EDW_DATA_EXPORT_PATH", "data/edw_exports") # For daily EDW feeds

    # --- External System Integration Settings (Placeholders) ---
    # These URLs would point to the actual external APIs in a real deployment.
    OFFERMART_API_URL: str = os.getenv("OFFERMART_API_URL", "http://offermart-service:8000/api")
    MOENGAGE_API_KEY: str = os.getenv("MOENGAGE_API_KEY", "your_moengage_api_key_here")
    CUSTOMER_360_API_URL: str = os.getenv("CUSTOMER_360_API_URL", "http://customer360-service:8000/api")
    LOS_API_URL: str = os.getenv("LOS_API_URL", "http://los-service:8000/api")
    # Add any other API keys or credentials for external systems here.

# Instantiate the settings object.
# This instance can be imported and used throughout the application.
settings = Settings()

# --- Directory Creation ---
# It's good practice to ensure necessary directories exist at application startup.
# This can be done here or in the main application entry point (e.g., main.py).
# Using exist_ok=True prevents errors if the directory already exists.
os.makedirs(settings.MOENGAGE_FILE_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_FILE_DIR, exist_ok=True)
os.makedirs(settings.DOWNLOAD_FILE_DIR, exist_ok=True)
os.makedirs(settings.EDW_DATA_EXPORT_PATH, exist_ok=True)