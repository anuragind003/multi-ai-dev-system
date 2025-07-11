from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Role(Base):
    """Represents a user role in the system."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    users = relationship("User", back_populates="role")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Role(name='{self.name}')>"

class Permission(Base):
    """Represents a specific action or resource access permission."""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False) # e.g., "user:read", "recording:download"
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Permission(name='{self.name}')>"

class RolePermission(Base):
    """Associates roles with permissions (many-to-many relationship)."""
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")

    __table_args__ = (UniqueConstraint('role_id', 'permission_id', name='_role_permission_uc'),)

    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"

class User(Base):
    """Represents a user in the system."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    role = relationship("Role", back_populates="users")

    recordings = relationship("Recording", back_populates="uploader")
    bulk_requests = relationship("BulkRequest", back_populates="requester")

    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role.name if self.role else 'N/A'}')>"

class Recording(Base):
    """Represents a V-KYC recording metadata."""
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    lan_id = Column(String(100), index=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False) # Path on NFS server
    file_size_bytes = Column(Integer, nullable=True)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    recording_date = Column(DateTime(timezone=True), nullable=True) # Actual date of recording
    status = Column(String(50), default="available") # e.g., "available", "archived", "deleted"
    metadata_json = Column(Text, nullable=True) # Store additional flexible metadata as JSON string

    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploader = relationship("User", back_populates="recordings")

    def __repr__(self):
        return f"<Recording(lan_id='{self.lan_id}', file_name='{self.file_name}')>"

class BulkRequest(Base):
    """Represents a request for bulk operations (e.g., bulk download, bulk upload status)."""
    __tablename__ = "bulk_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String(50), nullable=False) # e.g., "download", "upload_status"
    status = Column(String(50), default="pending", index=True) # e.g., "pending", "processing", "completed", "failed"
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requester = relationship("User", back_populates="bulk_requests")
    parameters_json = Column(Text, nullable=True) # JSON string of request parameters (e.g., list of LAN IDs)
    result_json = Column(Text, nullable=True) # JSON string of results/errors

    def __repr__(self):
        return f"<BulkRequest(type='{self.request_type}', status='{self.status}')>"