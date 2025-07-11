from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    """SQLAlchemy model for User."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Example relationship (if users can own recordings)
    # recordings = relationship("Recording", back_populates="owner")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

class Recording(Base):
    """SQLAlchemy model for VKYC Recording metadata."""
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    lan_id = Column(String, index=True, nullable=False, unique=True) # Unique identifier for the recording
    file_path = Column(String, nullable=False) # Path to the recording file on NFS
    file_name = Column(String, nullable=False) # Original file name
    duration_seconds = Column(Float, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    upload_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(String, default="available") # e.g., "available", "processing", "corrupted"
    metadata_json = Column(String, nullable=True) # Store additional metadata as JSON string

    # Example relationship (if recordings are associated with a user)
    # owner_id = Column(Integer, ForeignKey("users.id"))
    # owner = relationship("User", back_populates="recordings")

    def __repr__(self):
        return f"<Recording(id={self.id}, lan_id='{self.lan_id}', file_name='{self.file_name}')>"