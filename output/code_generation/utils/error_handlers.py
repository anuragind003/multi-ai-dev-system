### FILE: database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import get_settings
from utils.logger import logger

settings = get_settings()

# SQLAlchemy Async Engine
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)

# Async Session Local
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False # Important for keeping objects accessible after commit
)

Base = declarative_base()

async def init_db():
    """
    Initializes the database: creates tables if they don't exist.
    """
    async with engine.begin() as conn:
        # Drop all tables and recreate them for development/testing
        if settings.DEBUG:
            logger.info("Dropping all tables (DEBUG mode).")
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Creating database tables.")
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialization complete.")

async def get_db():
    """
    Dependency that provides an async database session.
    Ensures the session is closed after the request.
    """
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()