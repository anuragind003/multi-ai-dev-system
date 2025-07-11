from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool # Use NullPool for FastAPI if connection management is handled by lifespan events
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# SQLAlchemy Base for declarative models
Base = declarative_base()

# Async Engine and SessionLocal will be initialized on app startup
engine = None
AsyncSessionLocal = None

async def init_db():
    """
    Initializes the asynchronous database engine and session maker.
    Called during application startup.
    """
    global engine, AsyncSessionLocal
    try:
        engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=settings.DEBUG_MODE,  # Log SQL queries if debug mode is on
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            # Use NullPool if you manage connections via lifespan events and don't want SQLAlchemy's built-in pooling
            # For a web application, a connection pool is generally desired.
            # If using a connection pool, ensure it's properly configured for async.
            # For asyncpg, the default pool is usually fine, but explicit settings are good.
            # poolclass=NullPool # Uncomment if you want to disable SQLAlchemy's pooling
        )
        AsyncSessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False # Prevents objects from expiring after commit, useful for long-lived sessions
        )
        logger.info("Database engine and session maker initialized.")
        
        # Optional: Create tables if they don't exist (for development/testing)
        # In production, use Alembic for migrations.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables checked/created (if not existing).")

    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}", exc_info=True)
        raise

async def close_db_connection():
    """
    Closes the database engine connection pool.
    Called during application shutdown.
    """
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database engine disposed.")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injector for database sessions.
    Provides an asynchronous session to FastAPI endpoints and closes it after use.
    """
    if AsyncSessionLocal is None:
        logger.error("AsyncSessionLocal not initialized. Call init_db() first.")
        raise RuntimeError("Database not initialized.")

    db = AsyncSessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}", exc_info=True)
        await db.rollback() # Rollback on any exception
        raise
    finally:
        await db.close()
        logger.debug("Database session closed.")