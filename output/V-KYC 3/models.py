from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, Enum
from sqlalchemy.orm import relationship
from database import Base
import datetime
import enum

class VKYCRecordingStatus(str, enum.Enum):
    """Enum for VKYC recording statuses."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class UserRole(str, enum.Enum):
    """Enum for user roles."""
    ADMIN = "admin"
    AUDITOR = "auditor"
    VIEWER = "viewer"

class User(Base):
    """SQLAlchemy model for User."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

class VKYCRecording(Base):
    """SQLAlchemy model for VKYC Recording."""
    __tablename__ = "vkyc_recordings"

    id = Column(Integer, primary_key=True, index=True)
    lan_id = Column(String, index=True, nullable=False, unique=True) # Unique identifier for the customer
    recording_path = Column(String, nullable=False) # Path to the recording file on NFS
    recording_date = Column(DateTime, nullable=False) # Date of the recording
    status = Column(Enum(VKYCRecordingStatus), default=VKYCRecordingStatus.PENDING, nullable=False)
    uploaded_by = Column(String, nullable=False) # User who initiated the recording/upload
    review_notes = Column(String, nullable=True) # Notes from review process
    is_active = Column(Boolean, default=True, nullable=False) # Soft delete flag

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<VKYCRecording(id={self.id}, lan_id='{self.lan_id}', status='{self.status}')>"