from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from typing import AsyncGenerator

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# SQLAlchemy Async Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG_MODE,  # Log SQL queries if in debug mode
    pool_size=10,              # Max connections in pool
    max_overflow=20            # Max connections beyond pool_size
)

# Async Session Local
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False # Prevents objects from being expired after commit
)

Base = declarative_base()

async def init_db():
    """
    Initializes the database by creating all tables defined in Base.
    """
    async with engine.begin() as conn:
        try:
            # Drop all tables and recreate them for development/testing purposes
            # In production, use Alembic for migrations
            if settings.DEBUG_MODE:
                logger.warning("DEBUG_MODE is ON. Dropping and recreating all database tables.")
                await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified.")
        except SQLAlchemyError as e:
            logger.error(f"Error initializing database: {e}")
            raise

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an asynchronous database session.
    Ensures the session is closed after the request is processed.
    """
    db = AsyncSessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        await db.close()
        logger.debug("Database session closed.")