import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum

from db.database import Base

class BulkRequestStatusEnum(str, Enum):
    """
    Enum for the status of a bulk request.
    """
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class LanIdProcessingStatusEnum(str, Enum):
    """
    Enum for the processing status of an individual LAN ID.
    """
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING" # Initial state before processing

class BulkRequest(Base):
    """
    SQLAlchemy ORM model for a bulk request.
    Stores metadata about the request and its overall status.
    """
    __tablename__ = "bulk_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True) # User who initiated the request
    status = Column(SQLEnum(BulkRequestStatusEnum), default=BulkRequestStatusEnum.PENDING, nullable=False)
    metadata = Column(JSON, nullable=True) # e.g., filename, upload_timestamp, total_lan_ids
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to LanIdStatus records
    lan_id_statuses = relationship("LanIdStatus", back_populates="bulk_request", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BulkRequest(id={self.id}, status={self.status})>"

class LanIdStatus(Base):
    """
    SQLAlchemy ORM model for the status of each individual LAN ID within a bulk request.
    """
    __tablename__ = "lan_id_statuses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    bulk_request_id = Column(UUID(as_uuid=True), ForeignKey("bulk_requests.id"), nullable=False, index=True)
    lan_id = Column(String, nullable=False, index=True)
    status = Column(SQLEnum(LanIdProcessingStatusEnum), default=LanIdProcessingStatusEnum.PENDING, nullable=False)
    message = Column(String, nullable=True) # Error message if processing failed
    processed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship back to the BulkRequest
    bulk_request = relationship("BulkRequest", back_populates="lan_id_statuses")

    def __repr__(self):
        return f"<LanIdStatus(lan_id={self.lan_id}, status={self.status})>"