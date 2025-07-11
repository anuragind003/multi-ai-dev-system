import datetime
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base

class UserRole(str, enum.Enum):
    """Defines user roles for Role-Based Access Control."""
    ADMIN = "admin"
    USER = "user"

class User(Base):
    """SQLAlchemy model for users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    recordings = relationship("Recording", back_populates="uploader")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"

class RecordingStatus(str, enum.Enum):
    """Defines the status of a V-KYC recording."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"

class Recording(Base):
    """SQLAlchemy model for V-KYC recordings."""
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    lan_id = Column(String, index=True, nullable=False, comment="Loan Account Number ID")
    file_path = Column(String, unique=True, nullable=False, comment="Path to the recording file on NFS")
    file_name = Column(String, nullable=False, comment="Original file name of the recording")
    upload_date = Column(DateTime, default=datetime.datetime.now, nullable=False)
    status = Column(Enum(RecordingStatus), default=RecordingStatus.PENDING, nullable=False)
    notes = Column(Text, nullable=True, comment="Additional notes about the recording")
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    uploader = relationship("User", foreign_keys=[uploader_id], back_populates="recordings")
    approver = relationship("User", foreign_keys=[approved_by_id])

    def __repr__(self):
        return f"<Recording(id={self.id}, lan_id='{self.lan_id}', status='{self.status}')>"