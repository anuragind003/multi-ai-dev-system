from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create the SQLAlchemy engine
# `connect_args={"check_same_thread": False}` is needed for SQLite to allow multiple threads
# to interact with the database, which is common in web applications.
# For PostgreSQL/MySQL, this argument is not needed.
engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# Create a SessionLocal class
# Each instance of SessionLocal will be a database session.
# The `autocommit=False` means that the session will not commit changes automatically.
# The `autoflush=False` means that the session will not flush changes to the database automatically.
# `bind=engine` connects the session to our database engine.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our declarative models
Base = declarative_base()

def init_db():
    """
    Initializes the database by creating all tables defined in Base.
    This function should be called on application startup.
    """
    logger.info("Attempting to create database tables...")
    try:
        # Import models here to ensure they are registered with Base
        from app.models import User # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully or already exist.")
    except SQLAlchemyError as e:
        logger.error(f"Database initialization failed: {e}")
        raise # Re-raise to indicate a critical startup failure
    except Exception as e:
        logger.error(f"An unexpected error occurred during database initialization: {e}")
        raise

def get_db():
    """
    Dependency that provides a database session.
    It ensures the session is closed after the request is processed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()