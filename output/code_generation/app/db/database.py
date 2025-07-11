import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Engine
# echo=True will log all SQL statements, useful for debugging, set to False in production
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)

# SessionLocal class for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

def init_db():
    """
    Initializes the database by creating all tables defined in models.
    This function should be called during application startup.
    """
    try:
        logger.info("Attempting to create database tables...")
        # Import all models here to ensure they are registered with Base.metadata
        from app.db import models
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created or already exist.")
    except SQLAlchemyError as e:
        logger.critical(f"Failed to connect to database or create tables: {e}", exc_info=True)
        # In a real production environment, you might want to exit the application
        # or implement a retry mechanism here.
        raise
    except Exception as e:
        logger.critical(f"An unexpected error occurred during database initialization: {e}", exc_info=True)
        raise