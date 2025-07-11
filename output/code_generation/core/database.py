import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy asynchronous engine
# echo=True for debugging SQL queries (set to False in production)
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

# Asynchronous session factory
# expire_on_commit=False prevents objects from being expired after commit,
# allowing them to be accessed outside the session scope.
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for declarative models
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an asynchronous database session.
    Ensures the session is closed after the request is processed.
    """
    db = AsyncSessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}", exc_info=True)
        await db.rollback()
        raise
    finally:
        await db.close()
        logger.debug("Database session closed.")

def create_db_and_tables():
    """
    Synchronously creates all database tables defined by Base.metadata.
    This function is intended to be called at application startup.
    """
    import models.user_model # Import models to ensure they are registered with Base.metadata
    
    logger.info("Attempting to create database tables...")
    try:
        # Use a synchronous engine for table creation as it's a one-time setup
        # and Alembic is preferred for migrations in production.
        # This is for initial setup convenience.
        sync_engine = create_async_engine(settings.DATABASE_URL, echo=False, future=False).sync_engine
        Base.metadata.create_all(sync_engine)
        logger.info("Database tables created successfully (if not already existing).")
    except Exception as e:
        logger.critical(f"Error creating database tables: {e}", exc_info=True)
        raise # Re-raise to prevent application from starting if DB init fails