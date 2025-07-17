import logging
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.db.database import Base

logger = logging.getLogger(__name__)

class ParsedFile(Base):
    """
    SQLAlchemy model for storing metadata about parsed files.
    """
    __tablename__ = "parsed_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending") # e.g., "success", "failed", "partial_success"
    parsed_at = Column(DateTime(timezone=True), server_default=func.now())
    # Store LAN IDs as JSONB (PostgreSQL specific) or Text for other DBs
    # For PostgreSQL, use JSONB for efficient querying of array elements
    # For SQLite/MySQL, use Text and store as JSON string
    lan_ids = Column(JSON, nullable=False) # Stores list of validated LAN IDs
    errors = Column(JSON, nullable=True) # Stores list of errors for invalid LAN IDs

    def __repr__(self):
        return f"<ParsedFile(id={self.id}, filename='{self.filename}', status='{self.status}')>"

class User(Base):
    """
    Basic User model for authentication purposes (if implemented).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    is_active = Column(Integer, default=1) # Using Integer for boolean to be compatible with SQLite/MySQL

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

logger.info("Database models loaded.")