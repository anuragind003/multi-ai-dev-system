import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
# This ensures that environment variables defined in .env are loaded
# before the Settings class attempts to read them.
load_dotenv()

# --- Configuration ---
# Define a Pydantic Settings class to manage environment variables.
# This allows for easy validation and loading of configuration from .env files.
class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/cdp_db")

    # Pydantic-settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",  # Load variables from .env file
        extra="ignore"    # Ignore extra environment variables not defined here
    )

# Instantiate settings to load configuration
settings = Settings()

# --- Database Engine and Session Setup ---
# SQLAlchemy database URL, retrieved from the settings.
# Example format for PostgreSQL: "postgresql://user:password@host:port/dbname"
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create the SQLAlchemy engine.
# The engine is the starting point for all SQLAlchemy applications.
# It's responsible for managing connections to the database.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL
    # For production, consider adding pool_size, max_overflow, and pool_recycle
    # for better connection management.
    # e.g., pool_size=10, max_overflow=20, pool_recycle=3600
)

# Create a SessionLocal class.
# Each instance of SessionLocal will be a database session.
# The 'autocommit=False' means that changes are not committed automatically.
# The 'autoflush=False' means that objects are not flushed to the database automatically.
# 'bind=engine' links the session to our database engine.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative models.
# This Base class will be inherited by all SQLAlchemy models (tables) in our application.
Base = declarative_base()

# --- FastAPI Dependency for Database Session ---
# This function provides a database session to FastAPI route handlers.
# It ensures that a new session is created for each request and properly closed afterwards.
def get_db():
    """
    Dependency function to get a database session.

    Yields:
        sqlalchemy.orm.Session: A database session.
    """
    db = SessionLocal()
    try:
        yield db  # Provide the session to the caller
    finally:
        db.close() # Ensure the session is closed, even if an error occurs