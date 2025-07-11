import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG_MODE,  # Log SQL statements in debug mode
    pool_size=10,              # Max connections in pool
    max_overflow=20,           # Max connections beyond pool_size
    pool_timeout=30,           # Timeout for acquiring a connection
    pool_recycle=3600          # Recycle connections after 1 hour
)

# Async Session Local
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False # Prevents objects from expiring after commit
)

# Base for declarative models
Base = declarative_base()

async def init_db():
    """
    Initializes the database by creating all tables defined in Base.
    This is typically used for initial setup or testing.
    In production, Alembic migrations are preferred.
    """
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Use with caution for testing
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized.")

async def close_db():
    """
    Closes the database engine connection pool.
    """
    logger.info("Closing database connection pool...")
    await engine.dispose()
    logger.info("Database connection pool closed.")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an asynchronous database session.
    The session is automatically closed after the request is processed.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()