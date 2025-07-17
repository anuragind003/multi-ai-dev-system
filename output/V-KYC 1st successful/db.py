import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from config import get_settings
from error_handling import ServiceUnavailableException

logger = logging.getLogger("vkyc_api")
settings = get_settings()

# SQLAlchemy Engine
# `pool_pre_ping=True` ensures connections are still alive before use.
# `pool_recycle` helps prevent stale connections.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600, # Recycle connections after 1 hour
    echo=settings.DEBUG_MODE # Log SQL statements if in debug mode
)

# SQLAlchemy SessionLocal
# Each request will get its own SessionLocal instance.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

def get_db():
    """
    Dependency function to provide a SQLAlchemy session.
    Ensures the session is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error during request: {e}")
        raise ServiceUnavailableException(detail="Database operation failed.")
    finally:
        db.close()

def init_db():
    """
    Initializes the database by creating all tables defined in models.
    This should be called once on application startup.
    """
    try:
        logger.info("Attempting to connect to database and create tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created or already exist.")
    except SQLAlchemyError as e:
        logger.critical(f"Failed to connect to database or create tables: {e}")
        raise ServiceUnavailableException(detail="Failed to connect to database on startup.")