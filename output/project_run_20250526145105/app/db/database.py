from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Database URL from settings
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create the SQLAlchemy engine
# pool_pre_ping=True is useful for ensuring connections are still alive
# when retrieved from the pool, preventing stale connection errors.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True
)

# Create a SessionLocal class
# autocommit=False: This will prevent the session from committing changes automatically.
# autoflush=False: This will prevent the session from flushing changes to the database automatically.
# bind=engine: This binds the session to our database engine.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative models
# This Base class will be inherited by all our SQLAlchemy models.
Base = declarative_base()

# Dependency to get a database session
# This function will be used by FastAPI's Depends() to inject a database session
# into our path operations.
def get_db():
    """
    Dependency function that provides a SQLAlchemy database session.

    This function creates a new session for each request and ensures it is
    closed after the request is finished, even if errors occur.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()