from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Engine
# echo=True will log all SQL statements, useful for debugging
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=settings.DEBUG_MODE)

# SessionLocal class to create database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

def get_db():
    """
    Dependency function to provide a database session.
    Ensures the session is closed after the request is processed.
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error during request: {e}")
        db.rollback() # Rollback in case of error
        raise # Re-raise the exception
    finally:
        db.close()
        logger.debug("Database session closed.")

def create_tables():
    """
    Creates all database tables defined by Base.metadata.
    This function can be called on application startup.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created or already exist.")
    except SQLAlchemyError as e:
        logger.critical(f"Failed to create database tables: {e}")
        raise