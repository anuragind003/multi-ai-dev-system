from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from config import get_settings
from logger import logger

settings = get_settings()

# Use QueuePool for better connection management in a multi-threaded/async environment
# Adjust pool_size and max_overflow based on expected load
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30, # seconds
    pool_recycle=3600, # seconds (recycle connections older than 1 hour)
    echo=settings.DEBUG # Log SQL queries if debug is true
)

# Each instance of the SessionLocal class will be a database session.
# The `autocommit=False` ensures that changes are not committed until explicitly told.
# The `autoflush=False` ensures that objects are not flushed to the database until explicitly told.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency for FastAPI to provide a database session.
    Ensures the session is closed after the request is processed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        logger.debug("Database session closed.")

def init_db():
    """
    Initializes the database by creating all tables defined in models.
    This should be called once on application startup.
    """
    logger.info("Initializing database...")
    try:
        # Import all models here to ensure they are registered with Base
        from models import VKYCRecording, User # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully (if they didn't exist).")
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise