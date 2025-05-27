import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

# Load database URL from environment variables
# In a production environment, this would typically be set via Docker, Kubernetes, or CI/CD.
# For local development, you might use a .env file and a library like python-dotenv.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@db:5432/cdp_db")

# Create an asynchronous engine
# echo=True will log all SQL statements, useful for debugging
engine = create_async_engine(DATABASE_URL, echo=False)

# Create a sessionmaker for asynchronous sessions
# expire_on_commit=False prevents objects from being expired after commit,
# allowing them to be accessed outside the session scope (if carefully managed).
AsyncSessionLocal = async_sessionmaker(
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
    Dependency that provides a database session for each request.
    It ensures the session is properly closed after the request is handled.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()