from sqlalchemy import Column, Integer, String, DateTime, Boolean, ARRAY, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

# Define an Enum for Recording Status
class RecordingStatus(enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    ARCHIVED = "Archived"

class User(Base):
    """
    SQLAlchemy ORM model for User.
    Represents users who can access the V-KYC portal.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    roles = Column(ARRAY(String), default=["user"], nullable=False) # e.g., ["user", "admin"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', roles={self.roles})>"

class Recording(Base):
    """
    SQLAlchemy ORM model for Recording.
    Represents metadata for V-KYC recordings.
    """
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    lan_id = Column(String, unique=True, index=True, nullable=False) # Unique identifier for the recording
    customer_name = Column(String, index=True, nullable=False)
    recording_date = Column(DateTime(timezone=True), nullable=False)
    file_path = Column(String, unique=True, nullable=False) # Relative path to the file on NFS
    duration_seconds = Column(Integer, nullable=True)
    status = Column(Enum(RecordingStatus), default=RecordingStatus.PENDING, nullable=False) # e.g., Approved, Pending, Rejected
    notes = Column(Text, nullable=True)
    uploaded_by_user_id = Column(Integer, nullable=True) # Could be a foreign key to User.id
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Recording(id={self.id}, lan_id='{self.lan_id}', status='{self.status.value}')>"