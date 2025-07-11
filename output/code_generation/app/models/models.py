from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    """SQLAlchemy model for Users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    roles = Column(Text, nullable=False, default="user") # Comma-separated roles, e.g., "user,admin"
    is_active = Column(Integer, default=1) # Using Integer for boolean to be compatible with some DBs

    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', roles='{self.roles}')>"

class Recording(Base):
    """SQLAlchemy model for VKYC Recordings metadata."""
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    lan_id = Column(String, unique=True, index=True, nullable=False)
    file_path = Column(String, unique=True, nullable=False) # Path on NFS
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="available") # e.g., "available", "archived", "deleted"

    def __repr__(self):
        return f"<Recording(id={self.id}, lan_id='{self.lan_id}', path='{self.file_path}')>"

class AuditLog(Base):
    """SQLAlchemy model for Audit Logs."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False) # e.g., "download_recording", "login", "view_audit_logs"
    resource_type = Column(String, nullable=False) # e.g., "recording", "user"
    resource_id = Column(Integer, nullable=True) # ID of the resource acted upon (e.g., recording.id)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(JSON, nullable=True) # JSONB for additional context (e.g., IP, user_agent, file_name)

    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return (f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}', "
                f"resource_type='{self.resource_type}', resource_id={self.resource_id}, "
                f"timestamp='{self.timestamp}')>")