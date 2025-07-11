from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# SQLAlchemy Async Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL statements if debug is true
    pool_size=10,         # Max connections in pool
    max_overflow=20       # Max connections above pool_size
)

# Async Session Local
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False # Prevents objects from expiring after commit
)

# Base class for declarative models
Base = declarative_base()

async def init_db():
    """
    Initializes the database: creates tables if they don't exist.
    In a production environment, use Alembic for migrations.
    This is for development/initial setup convenience.
    """
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        # Drop all tables (for clean slate in dev, remove in prod)
        # await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialization complete.")

async def get_db():
    """
    Dependency to provide an asynchronous database session.
    Ensures the session is closed after the request.
    """
    db = AsyncSessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        await db.rollback() # Rollback on any exception
        raise # Re-raise the exception
    finally:
        await db.close()
        logger.debug("Database session closed.")