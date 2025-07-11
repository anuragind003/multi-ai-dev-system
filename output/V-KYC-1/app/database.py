import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from app.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Engine
# echo=True will log all SQL statements, useful for debugging, disable in production
engine = create_engine(settings.DATABASE_URL, echo=False)

# SessionLocal class for database sessions
# autocommit=False: Changes are not committed automatically
# autoflush=False: Session does not flush automatically on query
# bind=engine: Binds the session to our database engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our declarative models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get a database session.
    Yields a session and ensures it's closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()