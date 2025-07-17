from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from typing import Generator

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# SQLAlchemy database URL from settings
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create the SQLAlchemy engine
# pool_pre_ping=True helps with stale connections
# pool_recycle=3600 recycles connections after an hour
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_pre_ping=True, 
    pool_recycle=3600,
    echo=settings.DEBUG_MODE # Log SQL statements in debug mode
)

# Create a SessionLocal class
# autocommit=False: Changes are not committed automatically
# autoflush=False: Objects are not flushed to the database automatically
# bind=engine: Binds the session to our engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our declarative models
Base = declarative_base()

def get_db() -> Generator:
    """
    Dependency to get a database session.
    Yields a session and ensures it's closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error during request: {e}")
        db.rollback() # Rollback in case of an error
        raise
    finally:
        db.close()
        logger.debug("Database session closed.")