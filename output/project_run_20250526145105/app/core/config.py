from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core Application Settings
    APP_NAME: str = Field("LTFS Offer CDP", description="Name of the application")
    DEBUG: bool = Field(False, description="Enable debug mode for development")
    API_V1_STR: str = Field("/api/v1", description="Base path for API version 1 endpoints")

    # Database Settings (PostgreSQL)
    DATABASE_HOST: str = Field(..., description="PostgreSQL database host")
    DATABASE_PORT: int = Field(..., description="PostgreSQL database port")
    DATABASE_USER: str = Field(..., description="PostgreSQL database user")
    DATABASE_PASSWORD: str = Field(..., description="PostgreSQL database password")
    DATABASE_NAME: str = Field(..., description="PostgreSQL database name")

    @property
    def DATABASE_URL(self) -> PostgresDsn:
        """
        Constructs the full PostgreSQL connection URL.
        Uses 'postgresql+asyncpg' scheme for async database operations with SQLAlchemy.
        """
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            user=self.DATABASE_USER,
            password=self.DATABASE_PASSWORD,
            host=self.DATABASE_HOST,
            port=self.DATABASE_PORT,
            path=f"/{self.DATABASE_NAME}",
        )

    # Data Retention Policies (based on NFRs)
    OFFER_HISTORY_RETENTION_MONTHS: int = Field(
        6, description="Number of months to retain offer history data (NFR9)"
    )
    CDP_DATA_RETENTION_MONTHS: int = Field(
        3, description="Number of months to retain general CDP data before deletion (NFR10)"
    )
    MOENGAGE_FILE_RETENTION_DAYS: int = Field(
        7, description="Number of days to retain generated Moengage files on disk"
    )

    # External Service Base URLs (Placeholders - adjust as per actual integration details)
    CUSTOMER_360_API_BASE_URL: str = Field(
        "http://customer360.example.com/api",
        description="Base URL for Customer 360 API for deduplication checks",
    )
    OFFERMART_API_BASE_URL: str = Field(
        "http://offermart.example.com/api",
        description="Base URL for Analytics Offer Mart API for data ingestion/reverse feed",
    )
    MOENGAGE_API_BASE_URL: str = Field(
        "http://moengage.example.com/api",
        description="Base URL for Moengage API for campaign integration",
    )
    EDW_DATA_EXPORT_PATH: str = Field(
        "/app/data/edw_exports",
        description="Local file system path for daily EDW data exports",
    )


# Create a global settings instance to be imported throughout the application
settings = Settings()